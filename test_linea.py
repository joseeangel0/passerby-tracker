"""Pruebas de la logica de conteo. Corre con: python3 test_linea.py

No necesita video, ni YOLO, ni el entorno virtual: es python puro.
"""

# Import the functions and class that we want to test from linea.py
from linea import ContadorLineal, distancia_con_signo, pies


# Define a vertical counting line at x = 100.
# Because A -> B goes from top to bottom, points to the left of the line
# have a positive signed distance, which represents "entrada".
A, B = (100, 0), (100, 400)


# Creates a new counter with the same line and a 12-pixel dead zone.
# Using a function avoids repeating this setup in every test.
def nuevo():
    return ContadorLineal(A, B, margen=12)


# Sends a sequence of x positions to the counter.
# The y coordinate is always 200 because only the horizontal movement
# is relevant for these tests.
# The list comprehension keeps only actual crossing events.
def recorrer(c, tid, xs):
    return [e for x in xs if (e := c.actualizar(tid, (x, 200))) is not None]


# Test that moving from the right side to the left side counts as an entry.
def test_cruce_entrada():
    c = nuevo()

    # Person starts at x=200 (right), then moves to x=40 (left).
    ev = recorrer(c, 1, [200, 160, 40, 20])

    # Exactly one crossing should have been detected.
    assert len(ev) == 1, ev

    # The detected crossing must be an "entrada".
    assert ev[0]["direccion"] == "entrada"

    # There should be 1 entry and 0 exits.
    assert (c.entradas, c.salidas) == (1, 0)


# Test that moving from the left side to the right side counts as an exit.
def test_cruce_salida():
    c = nuevo()

    # Person starts on the left and moves to the right.
    ev = recorrer(c, 1, [20, 60, 160, 200])

    assert len(ev) == 1, ev
    assert ev[0]["direccion"] == "salida"

    # There should be 0 entries and 1 exit.
    assert (c.entradas, c.salidas) == (0, 1)


# Test the hysteresis/dead-zone behavior.
# A person moving slightly around the line should NOT trigger a crossing.
def test_jitter_sobre_la_linea_no_cuenta():
    c = nuevo()

    # All these x positions are within roughly 12 pixels of x=100.
    # Therefore, they remain inside the "dead zone".
    ev = recorrer(c, 1, [98, 102, 97, 103, 99, 101, 100, 104, 96])

    # No crossing should be detected.
    assert ev == [], ev

    # Counters must remain at zero.
    assert (c.entradas, c.salidas) == (0, 0)


# Moving toward the line and then returning to the original side
# should not count as a complete crossing.
def test_acercarse_y_regresar_no_cuenta():
    c = nuevo()

    # The person approaches the line, briefly crosses the dead zone,
    # but returns to the original side without confirming the opposite side.
    ev = recorrer(c, 1, [200, 150, 105, 95, 108, 150, 200])

    # No crossing should be registered.
    assert ev == [], ev


# Test a complete crossing in both directions.
def test_ida_y_vuelta_cuenta_las_dos():
    c = nuevo()

    # Person crosses from right -> left -> right.
    ev = recorrer(c, 1, [200, 20, 200])

    # The first crossing is an entry and the second is an exit.
    assert [e["direccion"] for e in ev] == ["entrada", "salida"], ev

    # One entry minus one exit results in a net count of zero.
    assert c.neto == 0


# Test that two different tracked people are handled independently.
def test_dos_personas_independientes():
    c = nuevo()

    # Person with track ID 1 starts on the right.
    c.actualizar(1, (200, 100))

    # Person with track ID 2 starts on the left.
    c.actualizar(2, (20, 300))

    # Person 1 crosses right -> left, so this is an entry.
    ev1 = c.actualizar(1, (20, 100))

    # Person 2 crosses left -> right, so this is an exit.
    ev2 = c.actualizar(2, (200, 300))

    # Verify that each event belongs to the correct person and direction.
    assert ev1["direccion"] == "entrada" and ev1["track_id"] == 1
    assert ev2["direccion"] == "salida" and ev2["track_id"] == 2

    # Total: 1 entry, 1 exit, net = 0.
    assert (c.entradas, c.salidas, c.neto) == (1, 1, 0)


# Test the pies() helper function.
# It should return the center of the bottom edge of a bounding box.
def test_pies_es_el_centro_inferior():
    assert pies(10, 20, 30, 80) == (20.0, 80)


# Test that distancia_con_signo() returns a distance measured in pixels.
def test_distancia_es_en_pixeles():

    # The point (50, 200) is exactly 50 pixels to the left
    # of the vertical line x=100.
    assert abs(distancia_con_signo(A, B, (50, 200)) - 50.0) < 1e-9


# This block runs only when this file is executed directly:
#     python3 test_linea.py
if __name__ == "__main__":

    # Find every function whose name starts with "test_".
    # sorted() makes the execution order predictable.
    pruebas = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

    # Execute every test function.
    for p in pruebas:
        p()

        # Print a confirmation when the test passes.
        print(f"  ok  {p.__name__}")

    # Print the total number of successful tests.
    print(f"\n{len(pruebas)} pruebas pasaron")