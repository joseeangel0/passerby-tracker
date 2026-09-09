"""Pruebas de la logica de conteo. Corre con: python3 test_linea.py

No necesita video, ni YOLO, ni el entorno virtual: es python puro.
"""

from linea import ContadorLineal, distancia_con_signo, pies

# Linea vertical en x=100. Con el orden A->B de abajo, el lado izquierdo
# (x menor) da positivo, o sea "entrada".
A, B = (100, 0), (100, 400)


def nuevo():
    return ContadorLineal(A, B, margen=12)


def recorrer(c, tid, xs):
    """Pasa una secuencia de posiciones x y junta los eventos."""
    return [e for x in xs if (e := c.actualizar(tid, (x, 200))) is not None]


def test_cruce_entrada():
    c = nuevo()
    ev = recorrer(c, 1, [200, 160, 40, 20])
    assert len(ev) == 1, ev
    assert ev[0]["direccion"] == "entrada"
    assert (c.entradas, c.salidas) == (1, 0)


def test_cruce_salida():
    c = nuevo()
    ev = recorrer(c, 1, [20, 60, 160, 200])
    assert len(ev) == 1, ev
    assert ev[0]["direccion"] == "salida"
    assert (c.entradas, c.salidas) == (0, 1)


def test_jitter_sobre_la_linea_no_cuenta():
    """El caso que arruina estos proyectos: alguien parado en la puerta."""
    c = nuevo()
    ev = recorrer(c, 1, [98, 102, 97, 103, 99, 101, 100, 104, 96])
    assert ev == [], ev
    assert (c.entradas, c.salidas) == (0, 0)


def test_acercarse_y_regresar_no_cuenta():
    c = nuevo()
    ev = recorrer(c, 1, [200, 150, 105, 95, 108, 150, 200])
    assert ev == [], ev


def test_ida_y_vuelta_cuenta_las_dos():
    c = nuevo()
    ev = recorrer(c, 1, [200, 20, 200])
    assert [e["direccion"] for e in ev] == ["entrada", "salida"], ev
    assert c.neto == 0


def test_dos_personas_independientes():
    c = nuevo()
    c.actualizar(1, (200, 100))
    c.actualizar(2, (20, 300))
    ev1 = c.actualizar(1, (20, 100))    # id 1 entra
    ev2 = c.actualizar(2, (200, 300))   # id 2 sale
    assert ev1["direccion"] == "entrada" and ev1["track_id"] == 1
    assert ev2["direccion"] == "salida" and ev2["track_id"] == 2
    assert (c.entradas, c.salidas, c.neto) == (1, 1, 0)


def test_pies_es_el_centro_inferior():
    assert pies(10, 20, 30, 80) == (20.0, 80)


def test_distancia_es_en_pixeles():
    # Un punto a 50 px a la izquierda de la linea mide 50, no un numero raro.
    assert abs(distancia_con_signo(A, B, (50, 200)) - 50.0) < 1e-9


if __name__ == "__main__":
    pruebas = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for p in pruebas:
        p()
        print(f"  ok  {p.__name__}")
    print(f"\n{len(pruebas)} pruebas pasaron")
