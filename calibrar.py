"""Define la linea de conteo sobre un frame del video y guarda config.json.
Uso normal (abre ventana, clicas dos puntos):
    python calibrar.py
Sin ventana, si el GUI no abre:
    python calibrar.py --puntos 640,300,640,900
"""

# argparse permite recibir parámetros desde la terminal.
import argparse
# json se utiliza para guardar la configuración en config.json.
import json
# math se utiliza para calcular la longitud del vector de la línea.
import math
# os permite comprobar si el archivo de video existe.
import os
# sys permite terminar el programa mostrando un mensaje de error.
import sys
# OpenCV se utiliza para leer el video, mostrar imágenes y dibujar la línea.
import cv2


# Nombre del archivo donde se almacenará toda la configuración.
CONFIG = "config.json"
# Ancho máximo de la ventana de calibración para evitar que sea demasiado grande.
ANCHO_MAX = 1280
def cargar_frame(video, segundo):
    """Carga un frame específico del video."""
    # Abrimos el archivo de video utilizando OpenCV.
    cap = cv2.VideoCapture(video)
    # Comprobamos que OpenCV haya podido abrir correctamente el video.
    if not cap.isOpened():
        sys.exit(f"No pude abrir el video: {video}")
    # Si se indicó un segundo específico, movemos el video hasta ese momento.
    if segundo > 0:
        cap.set(cv2.CAP_PROP_POS_MSEC, segundo * 1000)
    # Leemos un frame del video.
    ok, frame = cap.read()
    # Cerramos el archivo de video después de obtener el frame.
    cap.release()
    # Si no se pudo obtener el frame, terminamos el programa.
    if not ok:
        sys.exit(f"No pude leer un frame en el segundo {segundo}")
    # Regresamos la imagen obtenida.
    return frame


def normal_positiva(A, B):
    """Vector unitario que apunta al lado 'positivo' de la linea A->B.

    Debe coincidir con el signo de linea.distancia_con_signo.
    """

    # Calculamos el desplazamiento horizontal y vertical entre A y B.
    dx, dy = B[0] - A[0], B[1] - A[1]

    # Calculamos la longitud de la línea.
    # math.hypot evita tener que calcular manualmente sqrt(dx² + dy²).
    # Si la longitud fuera 0, usamos 1.0 para evitar división entre cero.
    largo = math.hypot(dx, dy) or 1.0

    # Convertimos el vector perpendicular (-dy, dx) en un vector unitario.
    # Este vector indica hacia qué lado de la línea se considera
    # que está la dirección "positiva".
    return (-dy / largo, dx / largo)


def dibujar(frame, A, B, nombre_pos):
    """Dibuja la línea, sus puntos y la flecha de dirección sobre el frame."""

    # Creamos una copia para no modificar el frame original.
    lienzo = frame.copy()

    # Dibujamos la línea de conteo entre los puntos A y B.
    cv2.line(lienzo, A, B, (0, 220, 0), 3)

    # Dibujamos un círculo sobre cada punto seleccionado.
    for P in (A, B):
        cv2.circle(lienzo, P, 7, (0, 220, 0), -1)

    # Calculamos el punto medio de la línea.
    medio = ((A[0] + B[0]) // 2, (A[1] + B[1]) // 2)

    # Obtenemos el vector que indica el lado positivo de la línea.
    nx, ny = normal_positiva(A, B)

    # Calculamos dónde terminará la flecha de dirección.
    punta = (int(medio[0] + nx * 70),
             int(medio[1] + ny * 70))

    # Dibujamos la flecha que muestra la dirección positiva.
    cv2.arrowedLine(
        lienzo,
        medio,
        punta,
        (0, 220, 255),
        3,
        tipLength=0.3
    )

    # Escribimos el nombre de la dirección junto a la flecha.
    cv2.putText(
        lienzo,
        nombre_pos,
        (punta[0] + 8, punta[1]),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 220, 255),
        2
    )

    # Regresamos la imagen ya dibujada.
    return lienzo


def barra_ayuda(lienzo, texto):
    """Agrega una barra inferior con las instrucciones de uso."""

    # Obtenemos la altura de la imagen.
    h = lienzo.shape[0]

    # Dibujamos un rectángulo negro en la parte inferior.
    cv2.rectangle(
        lienzo,
        (0, h - 34),
        (lienzo.shape[1], h),
        (0, 0, 0),
        -1
    )

    # Escribimos las instrucciones dentro de la barra.
    cv2.putText(
        lienzo,
        texto,
        (10, h - 11),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1
    )

    return lienzo


def calibrar_con_gui(frame, nombre_pos):
    """Permite seleccionar los dos puntos de la línea usando el mouse."""

    # Obtenemos las dimensiones originales del frame.
    alto, ancho = frame.shape[:2]

    # Calculamos una escala para que la ventana no supere ANCHO_MAX.
    escala = min(1.0, ANCHO_MAX / ancho)

    # Reducimos la imagen solamente si es demasiado grande.
    vista = (
        cv2.resize(frame, None, fx=escala, fy=escala)
        if escala < 1
        else frame
    )

    # Aquí almacenaremos los dos puntos seleccionados por el usuario.
    puntos = []

    def al_hacer_clic(evento, x, y, flags, param):
        """Función ejecutada cada vez que el usuario interactúa con el mouse."""

        # Solo nos interesa el clic izquierdo y permitimos máximo dos puntos.
        if evento == cv2.EVENT_LBUTTONDOWN and len(puntos) < 2:
            puntos.append((x, y))

    # Creamos la ventana donde se realizará la calibración.
    ventana = "Calibrar linea  -  clic en 2 puntos"
    cv2.namedWindow(ventana)

    # Conectamos nuestra función al evento de clic del mouse.
    cv2.setMouseCallback(ventana, al_hacer_clic)

    # Mantiene abierta la ventana hasta que el usuario elija una acción.
    while True:
        # Trabajamos sobre una copia de la imagen.
        lienzo = vista.copy()

        # Dibujamos los puntos que el usuario ya haya seleccionado.
        for P in puntos:
            cv2.circle(lienzo, P, 7, (0, 220, 0), -1)

        # Cuando existen exactamente dos puntos, mostramos la línea completa.
        if len(puntos) == 2:
            lienzo = dibujar(vista, *puntos, nombre_pos)

            # Mostramos las teclas disponibles.
            ayuda = "g = guardar   i = invertir lado   r = rehacer   ESC = salir"
        else:
            # Mientras faltan puntos, indicamos cuál debe seleccionar.
            ayuda = f"clic {len(puntos) + 1} de 2   |   r = rehacer   ESC = salir"

        # Mostramos la imagen y la barra de ayuda.
        cv2.imshow(ventana, barra_ayuda(lienzo, ayuda))

        # Esperamos 20 ms para detectar una tecla.
        tecla = cv2.waitKey(20) & 0xFF

        # ESC cancela el proceso sin guardar ninguna configuración.
        if tecla == 27:
            cv2.destroyAllWindows()
            sys.exit("Cancelado, no se guardo nada.")

        # "r" elimina los puntos seleccionados para poder empezar de nuevo.
        if tecla == ord("r"):
            puntos.clear()

        # "i" invierte el orden A -> B.
        # Esto también invierte el lado considerado como positivo.
        if len(puntos) == 2 and tecla == ord("i"):
            puntos.reverse()

        # "g" confirma los puntos y termina la selección.
        if len(puntos) == 2 and tecla == ord("g"):
            break

    # Cerramos la ventana de OpenCV.
    cv2.destroyAllWindows()

    # Los puntos fueron seleccionados sobre una imagen posiblemente reducida.
    # Aquí convertimos sus coordenadas nuevamente a la resolución original.
    return [
        (round(x / escala), round(y / escala))
        for x, y in puntos
    ]


def main():
    """Función principal del programa."""

    # Creamos el parser para recibir argumentos desde la terminal.
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Permite especificar qué video utilizar.
    p.add_argument("--video", default="videos/entrada.mp4")

    # Permite seleccionar el segundo del video del que se tomará el frame.
    p.add_argument(
        "--segundo",
        type=float,
        default=0,
        help="momento del video del que sacar el frame"
    )

    # Permite indicar directamente los dos puntos sin utilizar la ventana.
    p.add_argument(
        "--puntos",
        help="x1,y1,x2,y2 para saltarse la ventana"
    )

    # Nombre del lado positivo de la línea.
    p.add_argument(
        "--entrada",
        default="entrada",
        help="nombre del lado positivo (al que apunta la flecha)"
    )

    # Procesamos los argumentos proporcionados por el usuario.
    args = p.parse_args()

    # Comprobamos que el video especificado realmente exista.
    if not os.path.exists(args.video):
        sys.exit(
            f"No existe {args.video}. Pon tu video ahi o usa --video."
        )

    # Obtenemos un frame del video para utilizarlo durante la calibración.
    frame = cargar_frame(args.video, args.segundo)

    # Obtenemos la resolución del video.
    alto, ancho = frame.shape[:2]

    # Si el usuario proporcionó los puntos mediante --puntos,
    # evitamos abrir la ventana gráfica.
    if args.puntos:
        # Convertimos los valores separados por comas a números enteros.
        v = [int(n) for n in args.puntos.split(",")]

        # Deben existir exactamente cuatro valores:
        # x1, y1, x2, y2.
        if len(v) != 4:
            sys.exit(
                "--puntos necesita 4 numeros: x1,y1,x2,y2"
            )

        # Construimos los puntos A y B de la línea.
        A, B = (v[0], v[1]), (v[2], v[3])

    else:
        # Si no se proporcionaron coordenadas, abrimos el GUI
        # para que el usuario seleccione los dos puntos con el mouse.
        A, B = calibrar_con_gui(frame, args.entrada)

    # Creamos un diccionario con todos los parámetros necesarios
    # para que el programa contador.py pueda utilizar la calibración.
    config = {
        "video": args.video,

        # Coordenadas de los dos extremos de la línea.
        "linea": {"A": list(A), "B": list(B)},

        # Nombre del lado que se considera dirección positiva.
        "direccion_positiva": args.entrada,

        # El lado contrario se considera dirección negativa.
        "direccion_negativa": "salida",

        # Confianza mínima utilizada por el detector.
        "confianza": 0.35,

        # Margen de píxeles utilizado alrededor de la línea.
        "margen_px": 12,

        # Tamaño de imagen utilizado por el modelo.
        "imgsz": 640,

        # Ubicación donde se guardará el video procesado.
        "salida_video": "salida/resultado.mp4",

        # Ubicación donde se guardará el conteo en formato CSV.
        "salida_csv": "salida/conteo.csv",
    }

    # Abrimos/creamos config.json y guardamos la configuración.
    with open(CONFIG, "w") as f:
        json.dump(
            config,
            f,
            indent=2,
            ensure_ascii=False
        )

    # Guardamos una imagen mostrando la línea calibrada.
    # Esto permite revisar visualmente si la línea quedó en el lugar correcto.
    cv2.imwrite(
        "salida/linea.jpg",
        dibujar(frame, A, B, args.entrada)
    )

    # Mostramos información de la calibración en la terminal.
    print(f"Video   {args.video}  ({ancho}x{alto})")
    print(f"Linea   {A} -> {B}")

    # Mostramos el vector que representa el lado positivo.
    print(
        f"Lado positivo ('{args.entrada}') "
        f"hacia {normal_positiva(A, B)}"
    )

    # Confirmamos que la configuración fue guardada correctamente.
    print(
        f"\nGuardado en {CONFIG}. "
        f"Revisa salida/linea.jpg y corre: python contador.py"
    )


# Este bloque hace que main() se ejecute solamente cuando
# calibrar.py se ejecuta directamente, y no cuando se importa
# como módulo desde otro archivo.
if __name__ == "__main__":
    main()