# Contador de personas por cruce de línea

Cuenta cuántas personas cruzan una línea en un video y **en qué dirección**,
usando detección de objetos y seguimiento de trayectorias. El caso de uso
original: medir cuánta gente entra a una tienda.

Proyecto escolar. Todo el código es Python y corre en una laptop, sin GPU.

---

## Resultado de la prueba

Corrido sobre `videos/vtest.avi` (79 segundos, gente cruzando un patio):

| | |
|---|---|
| Cruces izquierda → derecha | 10 |
| Cruces derecha → izquierda | 13 |
| Personas distintas detectadas | 18 |
| Tiempo de proceso | 19 s para 795 frames (~42 fps) |

El video anotado está en [`salida/resultado.mp4`](salida/resultado.mp4) y los
datos crudos en [`salida/conteo.csv`](salida/conteo.csv), con un renglón por
cruce y el segundo exacto en que ocurrió.

**Estos números no están validados.** Nadie contó a mano ese video, así que
son lo que el sistema reporta, no necesariamente lo que pasó. Ver
[Validación](#validación).

---

## Cómo funciona

1. **Detección.** YOLO11-nano encuentra personas en cada frame. Se filtra a la
   clase `person` (clase 0 de COCO) y se ignora todo lo demás.

2. **Seguimiento.** ByteTrack le asigna un ID estable a cada persona para poder
   seguirla entre frames. Sin esto no se podría saber si dos detecciones en
   frames distintos son la misma persona.

3. **Punto de referencia.** De cada caja se toma el **centro-inferior** (los
   pies), no el centro. Es más estable: el centro de la caja se mueve cuando
   alguien levanta los brazos o cuando se le ocluye la cabeza, los pies no.

4. **Cruce con dirección.** Se calcula de qué lado de la línea cae ese punto
   usando el producto cruz 2D. Cuando el lado cambia, hubo un cruce, y el signo
   dice hacia dónde.

### La parte que evita el error más común

Hay una **franja muerta** de `margen_px` píxeles a cada lado de la línea donde
no se decide nada. Un track solo confirma de qué lado está cuando sale de esa
franja, y solo se cuenta un cruce cuando el lado confirmado *cambia*.

Sin esto, una persona parada justo sobre la línea haría temblar su caja de
detección y dispararía decenas de conteos falsos. Es el error clásico de estos
proyectos.

---

## Instalación

Requiere Python 3.12 (con 3.14 todavía fallan las ruedas de PyTorch).

```bash
git clone https://github.com/joseeangel0/passerby-tracker.git
cd passerby-tracker
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

El modelo `yolo11n.pt` (5 MB) se descarga solo la primera vez que corres el
programa. No está en el repo a propósito.

---

## Replicar la prueba

El repo ya trae el video y la configuración listos:

```bash
python contador.py
```

Tarda ~20 segundos y debe darte los mismos 10 y 13. Para ver el resultado:

```bash
open salida/resultado.mp4     # macOS
xdg-open salida/resultado.mp4 # Linux
```

Y las pruebas de la lógica de conteo, que no necesitan video ni modelo:

```bash
python test_linea.py
```

---

## Usarlo con tu propio video

**1. Define la línea.** Se abre una ventana con un frame del video; haces clic
en dos puntos sobre la puerta:

```bash
python calibrar.py --video videos/tu_video.mp4
```

- La flecha amarilla indica qué lado cuenta como positivo (`entrada`)
- `i` invierte la dirección · `g` guarda · `r` rehace · `ESC` cancela
- Si la ventana no abre: `python calibrar.py --video videos/tu_video.mp4 --puntos 640,300,640,900`

Pon la línea **dentro del marco de la puerta** y perpendicular al paso. Mientras
más lejos de la puerta, más oclusiones y más errores.

**2. Prueba con un tramo corto** antes de comprometerte al video completo:

```bash
python contador.py --hasta 60
```

**3. Revisa `salida/resultado.mp4`** y busca dónde el marcador brinca raro. Ahí
está tu ajuste (ver la tabla de abajo). Repite el paso 2 hasta que se vea bien.

**4. Corre el video completo:**

```bash
python contador.py
```

---

## Dashboard

`dashboard/aforo.html` es un panel que presenta los resultados como si fueran la
entrada de un restaurante: cuántos entraron, cuántos salieron, cuánta gente había
dentro en cada momento, y la bitácora completa de cruces.

Ábrelo con doble clic, no necesita servidor ni dependencias.

Los cruces son los reales que midió el sistema sobre `vtest.avi`. El encuadre de
restaurante es una simulación: cuál dirección es "hacia adentro" se decide al
calibrar la línea. Ninguna cifra proviene de un local real, y el panel lo dice.

## Estructura

| Archivo | Qué hace |
|---|---|
| `linea.py` | La lógica de cruce: signo, dirección, histéresis. Sin video ni YOLO |
| `calibrar.py` | Defines la línea con dos clics, escribe `config.json` |
| `contador.py` | Detecta, sigue, cuenta, escribe el CSV y el video anotado |
| `validar.py` | Compara contra tu conteo manual y saca la exactitud |
| `test_linea.py` | 8 pruebas de la lógica de conteo |
| `config.json` | La línea, el video y los parámetros. Lo genera `calibrar.py` |
| `salida/conteo.csv` | Un renglón por cruce: frame, segundo, ID, dirección |
| `salida/resultado.mp4` | El video con cajas, IDs y el marcador |

`linea.py` está separado a propósito: no importa OpenCV ni ultralytics, así que
se puede probar en milisegundos sin cargar el modelo.

---

## Ajustes en `config.json`

| Clave | Cuándo tocarla |
|---|---|
| `confianza` | Sube a 0.5 si detecta cosas que no son personas; baja a 0.25 si se le pasan |
| `margen_px` | Sube si cuenta de más por temblor; baja si se le pasan cruces rápidos |
| `imgsz` | 640 normal. 960 detecta gente lejana pero va más lento |
| `direccion_positiva` | Cómo se llama el lado al que apunta la flecha (`entrada`, `izq_a_der`, …) |

Los nombres de las direcciones se propagan al CSV, al marcador del video y a
`validar.py`. Si el CSV y el `config.json` no coinciden, `validar.py` avisa en
vez de reportar ceros en silencio.

---

## Validación

Sin esto, el proyecto es "el número que escupió el programa". Con esto, es "el
sistema tiene X% de exactitud y estos son sus modos de falla".

Cuenta a mano un tramo del video y llena `validacion.csv`:

```csv
inicio_s,fin_s,positivas_reales,negativas_reales
0,300,42,17
```

Luego:

```bash
python validar.py
python validar.py --por-minuto
```

Te da el error por tramo, el error total y el porcentaje de exactitud en cada
dirección. La primera vez genera la plantilla vacía.

**Ojo con la métrica:** compara totales por tramo, no persona por persona. Un
falso positivo y un falso negativo se cancelan entre sí, así que la exactitud
real puede ser peor de lo que indica.

---

## Sobre el valor `NETO`

Es cruces positivos menos negativos. En una tienda equivale a **cuánta gente hay
adentro**, pero solo si la tienda empezó vacía, todos usan esa puerta, y no hay
errores.

Ese último supuesto es el frágil: un error en un cruce afecta al total una vez,
pero **desplaza el neto para siempre**. El neto además arrastra los errores de
las dos direcciones a la vez.

Por eso conviene reportar los totales como resultado principal y el neto como
derivado, aclarando que su error crece con la duración del video.

**Como verificación gratis:** un neto negativo en una tienda que empezó vacía es
imposible. Si te sale negativo, es prueba de que el sistema está fallando.

---

## Limitaciones conocidas

- **Grupos apretados** que pasan juntos se detectan como menos personas.
- **Cambio de ID** tras una oclusión larga puede contar a alguien dos veces. En
  la prueba se asignaron 87 IDs para 18 personas que cruzaron.
- **Gente lejana o muy pequeña** en el cuadro se pierde. Sube `imgsz`.
- **Vista cenital pura no funciona.** YOLO viene entrenado con COCO, que es casi
  todo fotos a nivel de piso o en ángulo oblicuo. Una persona vista desde
  exactamente arriba no se parece a nada que el modelo haya aprendido. Esto
  descarta la mayoría de los datasets públicos de conteo, que están grabados
  desde el techo porque así se instalan los contadores comerciales.

---

## Notas

- `videos/vtest.avi` viene del repositorio de muestras de OpenCV
  ([samples/data](https://github.com/opencv/opencv/tree/4.x/samples/data)). Se
  incluye para que la prueba sea reproducible sin descargar nada.
- Es un patio abierto, no una puerta, así que las etiquetas ahí son
  `izq_a_der` / `der_a_izq` en vez de `entrada` / `salida`.
- El entorno virtual y el modelo `.pt` no están en el repo: se regeneran con
  `requirements.txt` y con la primera corrida.
