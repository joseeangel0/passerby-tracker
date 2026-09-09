"""Cuenta personas que entran y salen cruzando la linea de config.json.

    python contador.py                  # video completo
    python contador.py --hasta 60       # solo el primer minuto (para ajustar)
    python contador.py --mostrar        # ver el avance en vivo
"""

import argparse
import csv
import json
import os
import sys
import time

import cv2

from linea import ContadorLineal, pies

VERDE = (0, 220, 0)
AMBAR = (0, 220, 255)
GRIS = (200, 200, 200)


def cargar_config(ruta):
    if not os.path.exists(ruta):
        sys.exit(f"Falta {ruta}. Corre primero: python calibrar.py")
    with open(ruta) as f:
        return json.load(f)


def panel(frame, contador, seg, fps_proc):
    """Recuadro con el marcador. Sin acentos: cv2 no los dibuja bien.

    Los nombres salen de config.json para que el video diga lo mismo que
    el CSV. El recuadro se ajusta al texto mas largo.
    """
    pos = contador.nombre_positivo.upper()[:12]
    neg = contador.nombre_negativo.upper()[:12]
    filas = [
        (f"{pos:<12} {contador.entradas}", VERDE),
        (f"{neg:<12} {contador.salidas}", AMBAR),
        (f"{'NETO':<12} {contador.neto}", GRIS),
        (f"{seg:6.1f}s   {fps_proc:4.1f} fps", GRIS),
    ]
    ancho = max(cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0][0]
                for t, _ in filas[:3]) + 34
    cv2.rectangle(frame, (10, 10), (ancho, 122), (0, 0, 0), -1)
    for i, (texto, color) in enumerate(filas):
        escala = 0.7 if i < 3 else 0.45
        cv2.putText(frame, texto, (22, 42 + i * 26),
                    cv2.FONT_HERSHEY_SIMPLEX, escala, color, 2 if i < 3 else 1)
    return frame


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default="config.json")
    p.add_argument("--hasta", type=float, default=None,
                   help="procesar solo los primeros N segundos")
    p.add_argument("--mostrar", action="store_true", help="ventana en vivo")
    p.add_argument("--sin-video", action="store_true",
                   help="no escribir el video anotado (mas rapido)")
    p.add_argument("--modelo", default="yolo11n.pt")
    args = p.parse_args()

    cfg = cargar_config(args.config)
    A = tuple(cfg["linea"]["A"])
    B = tuple(cfg["linea"]["B"])

    from ultralytics import YOLO      # tarda en importar, hasta aqui no hace falta
    modelo = YOLO(args.modelo)

    cap = cv2.VideoCapture(cfg["video"])
    if not cap.isOpened():
        sys.exit(f"No pude abrir {cfg['video']}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    if args.hasta:
        total = min(total, int(args.hasta * fps)) if total else int(args.hasta * fps)

    contador = ContadorLineal(
        A, B,
        margen=cfg.get("margen_px", 12),
        nombre_positivo=cfg.get("direccion_positiva", "entrada"),
        nombre_negativo=cfg.get("direccion_negativa", "salida"),
    )

    os.makedirs(os.path.dirname(cfg["salida_csv"]) or ".", exist_ok=True)
    archivo_csv = open(cfg["salida_csv"], "w", newline="")
    escritor = csv.DictWriter(archivo_csv,
                              fieldnames=["frame", "segundo", "track_id", "direccion"])
    escritor.writeheader()

    escritor_video = None
    if not args.sin_video:
        escritor_video = cv2.VideoWriter(
            cfg["salida_video"], cv2.VideoWriter_fourcc(*"mp4v"), fps, (ancho, alto))

    print(f"Video    {cfg['video']}  {ancho}x{alto} @ {fps:.1f} fps")
    print(f"Linea    {A} -> {B}   margen {contador.margen}px")
    print(f"Modelo   {args.modelo}\n")

    resaltar = {}          # track_id -> frames que le quedan de resaltado
    n = 0
    inicio = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        seg = n / fps
        if args.hasta and seg > args.hasta:
            break

        r = modelo.track(frame, persist=True, classes=[0],
                         conf=cfg.get("confianza", 0.35),
                         imgsz=cfg.get("imgsz", 640),
                         tracker="bytetrack.yaml", verbose=False)[0]

        cajas = r.boxes
        if cajas is not None and cajas.id is not None:
            xyxy = cajas.xyxy.cpu().numpy()
            ids = cajas.id.int().cpu().tolist()
            for (x1, y1, x2, y2), tid in zip(xyxy, ids):
                punto = pies(x1, y1, x2, y2)
                evento = contador.actualizar(tid, punto, frame=n, segundo=seg)
                if evento:
                    escritor.writerow(evento)
                    archivo_csv.flush()
                    resaltar[tid] = int(fps // 2)

                activo = resaltar.get(tid, 0) > 0
                color = AMBAR if activo else VERDE
                if activo:
                    resaltar[tid] -= 1
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(frame, str(tid), (int(x1), int(y1) - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
                # El punto que realmente se mide contra la linea.
                cv2.circle(frame, (int(punto[0]), int(punto[1])), 4, color, -1)

        cv2.line(frame, A, B, VERDE, 3)
        fps_proc = (n + 1) / max(time.time() - inicio, 1e-6)
        panel(frame, contador, seg, fps_proc)

        if escritor_video:
            escritor_video.write(frame)
        if args.mostrar:
            cv2.imshow("contador  (q para cortar)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("\nCortado por el usuario.")
                break

        n += 1
        if n % 30 == 0:
            avance = f"{100 * n / total:5.1f}%" if total else f"{n} frames"
            print(f"\r  {avance}   entradas {contador.entradas}  "
                  f"salidas {contador.salidas}   {fps_proc:.1f} fps proc", end="")

    cap.release()
    archivo_csv.close()
    if escritor_video:
        escritor_video.release()
    if args.mostrar:
        cv2.destroyAllWindows()

    transcurrido = time.time() - inicio
    print(f"\r{' ' * 70}\r", end="")
    print(f"Listo. {n} frames en {transcurrido:.0f}s ({n / max(transcurrido, 1e-6):.1f} fps)\n")
    print(f"  {contador.nombre_positivo.upper():<12} {contador.entradas}")
    print(f"  {contador.nombre_negativo.upper():<12} {contador.salidas}")
    print(f"  {'NETO':<12} {contador.neto}")
    print(f"\nEventos en {cfg['salida_csv']}")
    if escritor_video:
        print(f"Video en   {cfg['salida_video']}  <- revisalo antes de confiar en el numero")


if __name__ == "__main__":
    main()
