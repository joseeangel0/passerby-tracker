"""Logica de conteo por cruce de linea.

No depende de video ni de YOLO a proposito: asi se puede probar sola
(ver test_linea.py). El resto del programa solo le pasa puntos.
"""

import math
from dataclasses import dataclass, field


def distancia_con_signo(A, B, P):
    """Distancia de P a la recta AB, en pixeles, con signo segun el lado.

    El signo sale del producto cruz 2D: positivo de un lado, negativo del
    otro. Cual lado es cual lo define el orden A->B, que fija calibrar.py.
    """
    dx, dy = B[0] - A[0], B[1] - A[1]
    largo = math.hypot(dx, dy)
    if largo == 0:
        raise ValueError("La linea necesita dos puntos distintos")
    cruz = dx * (P[1] - A[1]) - dy * (P[0] - A[0])
    return cruz / largo


def pies(x1, y1, x2, y2):
    """Centro-inferior de la caja: donde la persona pisa el piso.

    Mas estable que el centro del bbox, que se mueve si alguien levanta
    los brazos o si la cabeza se ocluye.
    """
    return ((x1 + x2) / 2.0, y2)


@dataclass
class ContadorLineal:
    """Cuenta cruces con direccion y con histeresis anti-rebote.

    La histeresis es una franja de `margen` pixeles a cada lado de la
    linea donde no se decide nada. Un track solo "confirma" lado cuando
    sale de esa franja, y solo se cuenta un cruce cuando el lado
    confirmado cambia. Alguien parado sobre la linea tiembla dentro de la
    franja sin disparar nada.
    """

    A: tuple
    B: tuple
    margen: float = 12.0
    nombre_positivo: str = "entrada"
    nombre_negativo: str = "salida"

    entradas: int = 0
    salidas: int = 0
    _lado: dict = field(default_factory=dict, repr=False)

    def actualizar(self, tid, punto, frame=0, segundo=0.0):
        """Procesa una posicion. Devuelve el evento si cruzo, si no None."""
        d = distancia_con_signo(self.A, self.B, punto)
        if abs(d) < self.margen:
            return None                      # franja muerta: sin opinion

        actual = 1 if d > 0 else -1
        previo = self._lado.get(tid)
        self._lado[tid] = actual

        if previo is None or previo == actual:
            return None                      # primera vez, o sin cambio

        if actual > 0:
            self.entradas += 1
            direccion = self.nombre_positivo
        else:
            self.salidas += 1
            direccion = self.nombre_negativo

        return {
            "frame": frame,
            "segundo": round(segundo, 2),
            "track_id": int(tid),
            "direccion": direccion,
        }

    @property
    def neto(self):
        """Personas dentro segun el conteo (entradas menos salidas)."""
        return self.entradas - self.salidas
