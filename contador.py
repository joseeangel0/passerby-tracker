"""Cuenta personas que entran y salen cruzando la linea de config.json.

    python contador.py                  # video completo
    python contador.py --hasta 60       # solo el primer minuto
    python contador.py --mostrar        # ver el avance en vivo
"""

# argparse permite configurar el programa mediante argumentos de terminal.
import argparse

# csv permite guardar los eventos de entrada y salida.
import csv

# json permite leer la configuración creada por calibrar.py.
import json

# os permite trabajar con rutas y crear carpetas.
import os

# sys permite terminar el programa mostrando errores.
import sys

# time se utiliza para medir cuánto tarda el procesamiento.
import time

# OpenCV se utiliza para leer, procesar y escribir los frames del video.
import cv2

# ContadorLineal contiene la lógica para detectar cruces de la línea.
# pies() obtiene el punto inferior central de cada bounding box.
from linea import ContadorLineal, pies


# Colores utilizados para dibujar los elementos sobre el video.
VERDE = (0, 220, 0)
AMBAR = (0, 220, 255)
GRIS = (200, 200, 200)


def cargar_config(ruta):
    """Carga la configuración almacenada en config.json."""

    # Comprobamos que el archivo de configuración exista.
    if not os.path.exists(ruta):
        sys.exit(f"Falta {ruta}. Corre primero: python calibrar.py")

    # Abrimos el archivo JSON.
    with open(ruta) as f:
        # Convertimos el JSON en un diccionario de Python.
        return json.load(f)


def panel(frame, contador, seg, fps_proc):
    """Dibuja el marcador de entradas, salidas y FPS sobre el video."""

    # Obtenemos los nombres de las direcciones desde el contador.
    pos = contador.nombre_positivo.upper()[:12]
    neg = contador.nombre_negativo.upper()[:12]

    # Creamos las filas que aparecerán en el marcador.
    filas = [
        (f"{pos:<12} {contador.entradas}", VERDE),
        (f"{neg:<12} {contador.salidas}", AMBAR),
        (f"{'NETO':<12} {contador.neto}", GRIS),
        (f"{seg:6.1f}s   {fps_proc:4.1f} fps", GRIS),
    ]

    # Calculamos el ancho necesario para que quepa el texto más largo.
    ancho = max(
        cv2.getTextSize(
            t,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            2
        )[0][0]
        for t, _ in filas[:3]
    ) + 34

    # Dibujamos el fondo negro del panel.
    cv2.rectangle(
        frame,
        (10, 10),
        (ancho, 122),
        (0, 0, 0),
        -1
    )

    # Dibujamos cada fila del marcador.
    for i, (texto, color) in enumerate(filas):
        escala = 0.7 if i < 3 else 0.45

        cv2.putText(
            frame,
            texto,
            (22, 42 + i * 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            escala,
            color,
            2 if i < 3 else 1
        )

    return frame


def main():
    """Función principal que procesa el video y cuenta los cruces."""

    # Creamos el parser para recibir opciones desde la terminal.
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Archivo de configuración utilizado por el programa.
    p.add_argument("--config", default="config.json")

    # Permite procesar únicamente los primeros N segundos del video.
    # Es útil para hacer pruebas sin procesar todo el video.
    p.add_argument(
        "--hasta",
        type=float,
        default=None,
        help="procesar solo los primeros N segundos"
    )

    # Si se utiliza, muestra el procesamiento en una ventana de OpenCV.
    p.add_argument(
        "--mostrar",
        action="store_true",
        help="ventana en vivo"
    )

    # Evita crear el video anotado para acelerar el procesamiento.
    p.add_argument(
        "--sin-video",
        action="store_true",
        help="no escribir el video anotado (mas rapido)"
    )

    # Modelo YOLO que se utilizará para detectar y rastrear personas.
    p.add_argument("--modelo", default="yolo11n.pt")

    # Procesamos todos los argumentos proporcionados.
    args = p.parse_args()

    # Cargamos la configuración creada anteriormente por calibrar.py.
    cfg = cargar_config(args.config)

    # Recuperamos los dos extremos de la línea de conteo.
    A = tuple(cfg["linea"]["A"])
    B = tuple(cfg["linea"]["B"])

    # Importamos YOLO aquí para evitar cargarlo si el programa
    # todavía no ha validado la configuración.
    from ultralytics import YOLO

    # Cargamos el modelo YOLO seleccionado.
    modelo = YOLO(args.modelo)

    # Abrimos el video que está indicado en config.json.
    cap = cv2.VideoCapture(cfg["video"])

    # Verificamos que el video se haya podido abrir.
    if not cap.isOpened():
        sys.exit(f"No pude abrir {cfg['video']}")

    # Obtenemos los FPS originales del video.
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    # Obtenemos el ancho y alto de cada frame.
    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Obtenemos la cantidad total de frames del video.
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

    # Si se especificó --hasta, limitamos la cantidad de frames
    # que se procesarán.
    if args.hasta:
        total = (
            min(total, int(args.hasta * fps))
            if total
            else int(args.hasta * fps)
        )

    # Creamos el contador encargado de determinar cuándo una persona
    # cruza la línea y en qué dirección lo hizo.
    contador = ContadorLineal(
        A,
        B,

        # Margen alrededor de la línea donde se considera un posible cruce.
        margen=cfg.get("margen_px", 12),

        # Nombre del lado positivo, normalmente "entrada".
        nombre_positivo=cfg.get("direccion_positiva", "entrada"),

        # Nombre del lado negativo, normalmente "salida".
        nombre_negativo=cfg.get("direccion_negativa", "salida"),
    )

    # Creamos la carpeta de salida si todavía no existe.
    os.makedirs(
        os.path.dirname(cfg["salida_csv"]) or ".",
        exist_ok=True
    )

    # Abrimos el archivo CSV donde se almacenarán los eventos.
    archivo_csv = open(
        cfg["salida_csv"],
        "w",
        newline=""
    )

    # Definimos las columnas que tendrá el CSV.
    escritor = csv.DictWriter(
        archivo_csv,
        fieldnames=[
            "frame",
            "segundo",
            "track_id",
            "direccion"
        ]
    )

    # Escribimos la primera fila con los nombres de las columnas.
    escritor.writeheader()

    # El escritor del video comienza como None.
    escritor_video = None

    # Solo creamos el video de salida si el usuario no utilizó --sin-video.
    if not args.sin_video:
        escritor_video = cv2.VideoWriter(
            cfg["salida_video"],
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (ancho, alto)
        )

    # Mostramos información básica del procesamiento.
    print(
        f"Video    {cfg['video']}  "
        f"{ancho}x{alto} @ {fps:.1f} fps"
    )
    print(
        f"Linea    {A} -> {B}   "
        f"margen {contador.margen}px"
    )
    print(f"Modelo   {args.modelo}\n")

    # Diccionario utilizado para mantener resaltadas durante algunos
    # frames a las personas que acaban de cruzar.
    # Formato: track_id -> frames restantes.
    resaltar = {}

    # Contador del frame actual.
    n = 0

    # Guardamos el momento en que comenzó el procesamiento.
    inicio = time.time()

    # Procesamos el video frame por frame.
    while True:

        # Leemos el siguiente frame.
        ok, frame = cap.read()

        # Si no quedan frames, terminamos el ciclo.
        if not ok:
            break

        # Calculamos el tiempo del frame actual en segundos.
        seg = n / fps

        # Si se estableció un límite de tiempo, dejamos de procesar
        # cuando se alcanza.
        if args.hasta and seg > args.hasta:
            break

        # YOLO detecta y rastrea objetos en el frame.
        #
        # classes=[0] significa que solo queremos detectar personas.
        # persist=True mantiene los IDs entre frames.
        # conf establece la confianza mínima de detección.
        # imgsz define el tamaño utilizado por el modelo.
        # ByteTrack asigna y mantiene los IDs de cada persona.
        r = modelo.track(
            frame,
            persist=True,
            classes=[0],
            conf=cfg.get("confianza", 0.35),
            imgsz=cfg.get("imgsz", 640),
            tracker="bytetrack.yaml",
            verbose=False
        )[0]

        # Obtenemos las bounding boxes detectadas por YOLO.
        cajas = r.boxes

        # Verificamos que existan cajas y que tengan IDs de tracking.
        if cajas is not None and cajas.id is not None:

            # Convertimos las coordenadas de las cajas a NumPy.
            xyxy = cajas.xyxy.cpu().numpy()

            # Obtenemos los IDs asignados a cada persona.
            ids = cajas.id.int().cpu().tolist()

            # Recorremos cada persona detectada junto con su ID.
            for (x1, y1, x2, y2), tid in zip(xyxy, ids):

                # Calculamos el punto inferior central de la persona.
                # Este punto representa aproximadamente sus pies.
                punto = pies(x1, y1, x2, y2)

                # Enviamos el ID y la posición al contador.
                # Si cruzó la línea, devuelve un evento.
                evento = contador.actualizar(
                    tid,
                    punto,
                    frame=n,
                    segundo=seg
                )

                # Si ocurrió un cruce, lo guardamos en el CSV.
                if evento:
                    escritor.writerow(evento)

                    # Forzamos que el evento se escriba inmediatamente.
                    archivo_csv.flush()

                    # Hacemos que la persona se resalte temporalmente.
                    resaltar[tid] = int(fps // 2)

                # Comprobamos si esta persona debe seguir resaltada.
                activo = resaltar.get(tid, 0) > 0

                # Las personas que acaban de cruzar se muestran en ámbar.
                # Las demás se muestran en verde.
                color = AMBAR if activo else VERDE

                # Reducimos el tiempo restante del resaltado.
                if activo:
                    resaltar[tid] -= 1

                # Dibujamos la bounding box de la persona.
                cv2.rectangle(
                    frame,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    color,
                    2
                )

                # Mostramos el ID de tracking encima de la persona.
                cv2.putText(
                    frame,
                    str(tid),
                    (int(x1), int(y1) - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    color,
                    2
                )

                # Dibujamos el punto de los pies.
                # Este es el punto que realmente se compara con la línea.
                cv2.circle(
                    frame,
                    (int(punto[0]), int(punto[1])),
                    4,
                    color,
                    -1
                )

        # Dibujamos la línea de conteo sobre el frame.
        cv2.line(frame, A, B, VERDE, 3)

        # Calculamos la velocidad real de procesamiento.
        fps_proc = (
            (n + 1) /
            max(time.time() - inicio, 1e-6)
        )

        # Agregamos el panel con las estadísticas.
        panel(
            frame,
            contador,
            seg,
            fps_proc
        )

        # Si está habilitado, guardamos el frame procesado en el video.
        if escritor_video:
            escritor_video.write(frame)

        # Si se solicitó --mostrar, mostramos el frame en vivo.
        if args.mostrar:
            cv2.imshow(
                "contador  (q para cortar)",
                frame
            )

            # La tecla "q" permite detener el procesamiento manualmente.
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("\nCortado por el usuario.")
                break

        # Pasamos al siguiente frame.
        n += 1

        # Cada 30 frames mostramos el progreso en la terminal.
        if n % 30 == 0:
            avance = (
                f"{100 * n / total:5.1f}%"
                if total
                else f"{n} frames"
            )

            print(
                f"\r  {avance}   "
                f"entradas {contador.entradas}  "
                f"salidas {contador.salidas}   "
                f"{fps_proc:.1f} fps proc",
                end=""
            )

    # Liberamos el video de entrada.
    cap.release()

    # Cerramos el archivo CSV.
    archivo_csv.close()

    # Si se creó un video de salida, lo cerramos correctamente.
    if escritor_video:
        escritor_video.release()

    # Cerramos cualquier ventana de OpenCV que siga abierta.
    if args.mostrar:
        cv2.destroyAllWindows()

    # Calculamos cuánto tiempo tomó todo el procesamiento.
    transcurrido = time.time() - inicio

    # Mostramos un resumen final.
    print(
        f"\r{' ' * 70}\r"
        f"Listo. {n} frames en {transcurrido:.0f}s "
        f"({n / max(transcurrido, 1e-6):.1f} fps)\n"
    )

    # Mostramos el total de entradas.
    print(
        f"  {contador.nombre_positivo.upper():<12} "
        f"{contador.entradas}"
    )

    # Mostramos el total de salidas.
    print(
        f"  {contador.nombre_negativo.upper():<12} "
        f"{contador.salidas}"
    )

    # Mostramos la diferencia entre entradas y salidas.
    print(
        f"  {'NETO':<12} "
        f"{contador.neto}"
    )

    # Indicamos dónde se guardaron los eventos.
    print(f"\nEventos en {cfg['salida_csv']}")

    # Si se generó el video, mostramos su ubicación.
    if escritor_video:
        print(
            f"Video en   {cfg['salida_video']}  "
            f"<- revisalo antes de confiar en el numero"
        )


# Ejecutamos main() solamente si este archivo se ejecuta directamente.
# Si contador.py fuera importado desde otro archivo, main() no se ejecutaría.
if __name__ == "__main__":
    main()