"""Compara el conteo del sistema contra tu conteo manual.

Los nombres de las direcciones salen de config.json, asi que funciona
igual si les pusiste entrada/salida o izq_a_der/der_a_izq.

Llena validacion.csv con los tramos que contaste a mano. Las columnas
'positivas' y 'negativas' son las dos direcciones, en el mismo orden que
config.json:

    inicio_s,fin_s,positivas_reales,negativas_reales
    0,300,42,17

Luego:
    python validar.py
    python validar.py --por-minuto
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter

CONTEO = "salida/conteo.csv"
VALIDACION = "validacion.csv"


def nombres(ruta="config.json"):
    """Como se llaman las dos direcciones. Sin config, los de siempre."""
    try:
        with open(ruta) as f:
            cfg = json.load(f)
        return (cfg.get("direccion_positiva", "entrada"),
                cfg.get("direccion_negativa", "salida"))
    except (OSError, json.JSONDecodeError):
        return "entrada", "salida"


def leer_eventos(ruta):
    if not os.path.exists(ruta):
        sys.exit(f"Falta {ruta}. Corre primero: python contador.py")
    with open(ruta) as f:
        return [
            {"segundo": float(r["segundo"]), "direccion": r["direccion"],
             "track_id": int(r["track_id"])}
            for r in csv.DictReader(f)
        ]


def contar_en(eventos, inicio, fin):
    return Counter(e["direccion"] for e in eventos if inicio <= e["segundo"] < fin)


def exactitud(sistema, real):
    if real == 0:
        return 100.0 if sistema == 0 else 0.0
    return max(0.0, 100.0 * (1 - abs(sistema - real) / real))


def plantilla(pos, neg):
    return (f"# tramos que contaste a mano. positivas={pos}, negativas={neg}\n"
            "inicio_s,fin_s,positivas_reales,negativas_reales\n"
            "0,300,0,0\n")


def tabla_por_minuto(eventos, pos, neg):
    if not eventos:
        return
    ultimo = int(max(e["segundo"] for e in eventos) // 60) + 1
    print(f"\nCruces por minuto\n")
    print(f"  {'min':>4}  {pos:>12}  {neg:>12}")
    for m in range(ultimo):
        c = contar_en(eventos, m * 60, (m + 1) * 60)
        a, b = c.get(pos, 0), c.get(neg, 0)
        print(f"  {m:>4}  {a:>12}  {b:>12}  {'#' * a}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--conteo", default=CONTEO)
    p.add_argument("--validacion", default=VALIDACION)
    p.add_argument("--config", default="config.json")
    p.add_argument("--por-minuto", action="store_true")
    args = p.parse_args()

    pos, neg = nombres(args.config)
    eventos = leer_eventos(args.conteo)

    # Si el CSV trae etiquetas que no reconozco, es que se corrio con otra
    # config. Mejor avisar que reportar ceros en silencio.
    vistas = {e["direccion"] for e in eventos}
    if vistas - {pos, neg}:
        print(f"AVISO: {args.conteo} tiene direcciones {sorted(vistas)}, pero "
              f"{args.config} dice ('{pos}', '{neg}').")
        print("       Vuelve a correr contador.py, o pasa el config correcto.\n")

    total = Counter(e["direccion"] for e in eventos)
    print(f"Sistema: {total.get(pos, 0)} {pos}, {total.get(neg, 0)} {neg}, "
          f"{len({e['track_id'] for e in eventos})} personas distintas")

    if args.por_minuto:
        tabla_por_minuto(eventos, pos, neg)

    if not os.path.exists(args.validacion):
        with open(args.validacion, "w") as f:
            f.write(plantilla(pos, neg))
        print(f"\nCree la plantilla {args.validacion}. Cuenta a mano un tramo del")
        print("video, llena los numeros reales y vuelve a correr esto.")
        return

    with open(args.validacion) as f:
        tramos = [r for r in csv.DictReader(
            l for l in f if not l.startswith("#"))]

    print(f"\n{'tramo':>14}  {'sis':>5} {'real':>5} {'err':>5}  "
          f"{'sis':>5} {'real':>5} {'err':>5}")
    print(f"{'':>14}  {pos:^17}  {neg:^17}")
    print("  " + "-" * 58)

    sp = rp = sn = rn = 0
    for t in tramos:
        ini, fin = float(t["inicio_s"]), float(t["fin_s"])
        c = contar_en(eventos, ini, fin)
        a, ra = c.get(pos, 0), int(t["positivas_reales"])
        b, rb = c.get(neg, 0), int(t["negativas_reales"])
        sp += a; rp += ra; sn += b; rn += rb
        print(f"{ini:>6.0f}-{fin:<7.0f}  {a:>5} {ra:>5} {a - ra:>+5}  "
              f"{b:>5} {rb:>5} {b - rb:>+5}")

    print("  " + "-" * 58)
    print(f"{'TOTAL':>14}  {sp:>5} {rp:>5} {sp - rp:>+5}  {sn:>5} {rn:>5} {sn - rn:>+5}")
    print(f"\n  Exactitud en {pos}: {exactitud(sp, rp):.1f}%")
    print(f"  Exactitud en {neg}: {exactitud(sn, rn):.1f}%")
    print("\n  Nota: esto compara totales por tramo, no persona por persona.")
    print("  Un falso positivo y un falso negativo se cancelan entre si.")


if __name__ == "__main__":
    main()
