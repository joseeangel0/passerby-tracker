"""Define la linea de conteo sobre un frame del video y guarda config.json.

Uso normal (abre ventana, clicas dos puntos):
    python calibrar.py

Sin ventana, si el GUI no abre:
    python calibrar.py --puntos 640,300,640,900
"""

import argparse
import json
import math
import os
import sys

import cv2

CONFIG = "config.json"
ANCHO_MAX = 1280          # la ventana no crece mas que esto


def cargar_frame(video, segundo):
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        sys.exit(f"No pude abrir el video: {video}")
    if segundo > 0:
        cap.set(cv2.CAP_PROP_POS_MSEC, segundo * 1000)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        sys.exit(f"No pude leer un frame en el segundo {segundo}")
    return frame


def normal_positiva(A, B):
    """Vector unitario que apunta al lado 'positivo' de la linea A->B.

    Debe coincidir con el signo de linea.distancia_con_signo: ahi el cruz
    es dx*(Py-Ay) - dy*(Px-Ax), que es positivo para el vector (-dy, dx).
    """
    dx, dy = B[0] - A[0], B[1] - A[1]
    largo = math.hypot(dx, dy) or 1.0
    return (-dy / largo, dx / largo)


def dibujar(frame, A, B, nombre_pos):
    lienzo = frame.copy()
    cv2.line(lienzo, A, B, (0, 220, 0), 3)
    for P in (A, B):
        cv2.circle(lienzo, P, 7, (0, 220, 0), -1)

    # Flecha desde el centro hacia el lado que se contara como positivo.
    medio = ((A[0] + B[0]) // 2, (A[1] + B[1]) // 2)
    nx, ny = normal_positiva(A, B)
    punta = (int(medio[0] + nx * 70), int(medio[1] + ny * 70))
    cv2.arrowedLine(lienzo, medio, punta, (0, 220, 255), 3, tipLength=0.3)
    cv2.putText(lienzo, nombre_pos, (punta[0] + 8, punta[1]),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 220, 255), 2)
    return lienzo


def barra_ayuda(lienzo, texto):
    h = lienzo.shape[0]
    cv2.rectangle(lienzo, (0, h - 34), (lienzo.shape[1], h), (0, 0, 0), -1)
    cv2.putText(lienzo, texto, (10, h - 11),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return lienzo


def calibrar_con_gui(frame, nombre_pos):
    alto, ancho = frame.shape[:2]
    escala = min(1.0, ANCHO_MAX / ancho)
    vista = cv2.resize(frame, None, fx=escala, fy=escala) if escala < 1 else frame

    puntos = []

    def al_hacer_clic(evento, x, y, flags, param):
        if evento == cv2.EVENT_LBUTTONDOWN and len(puntos) < 2:
            puntos.append((x, y))

    ventana = "Calibrar linea  -  clic en 2 puntos"
    cv2.namedWindow(ventana)
    cv2.setMouseCallback(ventana, al_hacer_clic)

    while True:
        lienzo = vista.copy()
        for P in puntos:
            cv2.circle(lienzo, P, 7, (0, 220, 0), -1)
        if len(puntos) == 2:
            lienzo = dibujar(vista, *puntos, nombre_pos)
            ayuda = "g = guardar   i = invertir lado   r = rehacer   ESC = salir"
        else:
            ayuda = f"clic {len(puntos) + 1} de 2   |   r = rehacer   ESC = salir"
        cv2.imshow(ventana, barra_ayuda(lienzo, ayuda))

        tecla = cv2.waitKey(20) & 0xFF
        if tecla == 27:
            cv2.destroyAllWindows()
            sys.exit("Cancelado, no se guardo nada.")
        if tecla == ord("r"):
            puntos.clear()
        if len(puntos) == 2 and tecla == ord("i"):
            puntos.reverse()            # invertir A y B voltea el signo
        if len(puntos) == 2 and tecla == ord("g"):
            break

    cv2.destroyAllWindows()
    # Regresar las coordenadas a la resolucion real del video.
    return [(round(x / escala), round(y / escala)) for x, y in puntos]


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--video", default="videos/entrada.mp4")
    p.add_argument("--segundo", type=float, default=0,
                   help="momento del video del que sacar el frame")
    p.add_argument("--puntos", help="x1,y1,x2,y2 para saltarse la ventana")
    p.add_argument("--entrada", default="entrada",
                   help="nombre del lado positivo (al que apunta la flecha)")
    args = p.parse_args()

    if not os.path.exists(args.video):
        sys.exit(f"No existe {args.video}. Pon tu video ahi o usa --video.")

    frame = cargar_frame(args.video, args.segundo)
    alto, ancho = frame.shape[:2]

    if args.puntos:
        v = [int(n) for n in args.puntos.split(",")]
        if len(v) != 4:
            sys.exit("--puntos necesita 4 numeros: x1,y1,x2,y2")
        A, B = (v[0], v[1]), (v[2], v[3])
    else:
        A, B = calibrar_con_gui(frame, args.entrada)

    config = {
        "video": args.video,
        "linea": {"A": list(A), "B": list(B)},
        "direccion_positiva": args.entrada,
        "direccion_negativa": "salida",
        "confianza": 0.35,
        "margen_px": 12,
        "imgsz": 640,
        "salida_video": "salida/resultado.mp4",
        "salida_csv": "salida/conteo.csv",
    }
    with open(CONFIG, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # Dejar una imagen de la linea para revisarla o meterla al reporte.
    cv2.imwrite("salida/linea.jpg", dibujar(frame, A, B, args.entrada))

    print(f"Video   {args.video}  ({ancho}x{alto})")
    print(f"Linea   {A} -> {B}")
    print(f"Lado positivo ('{args.entrada}') hacia {normal_positiva(A, B)}")
    print(f"\nGuardado en {CONFIG}. Revisa salida/linea.jpg y corre: python contador.py")


if __name__ == "__main__":
    main()
