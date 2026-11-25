"""Motor de tarifas (T3.2 — §3.2 de la especificación).

Regla de prioridad estricta, bloque a bloque:

    Fecha Especial  >  Tarifa Semanal  >  Precio Base

- La unidad de cálculo es el **bloque de 60 minutos**. Un rango de reserva se
  descompone en bloques alineados (R4) y se suma el precio de cada bloque.
- R10: todos los bloques deben caer **dentro de una franja de operación activa**
  del día; un rango que cruza un hueco (p. ej. 11:00-14:00 con franjas
  08-12 y 13-22) es rechazado.
- Sólo cuentan tarifas `activo=True`.

Este módulo es una función pura: no toca la base de datos salvo para leer los
horarios/tarifas que se le pasan desde el servicio.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from shared.exceptions import FUERA_DE_HORARIO, BusinessRuleViolation
from shared.validators import assert_valid_booking_range

from modules.fields.models import Cancha, HorarioOperacion, Tarifa

ORIGEN_BASE = "base"
ORIGEN_SEMANAL = "semanal"
ORIGEN_ESPECIAL = "especial"


@dataclass(frozen=True)
class Bloque:
    """Un bloque de 60 minutos con su precio y el origen de ese precio."""

    hora_inicio: dt.time
    hora_fin: dt.time
    precio: Decimal
    origen: str
    tarifa_id: int | None = None

    @property
    def clave(self) -> str:
        return f"{self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}"


def _franjas_del_dia(cancha: Cancha, fecha: dt.date) -> list[HorarioOperacion]:
    return [h for h in cancha.horarios.all() if h.activo and h.dia_semana == fecha.isoweekday()]


def _dentro_de_franja(franjas: list[HorarioOperacion], inicio: dt.time, fin: dt.time) -> bool:
    return any(h.hora_apertura <= inicio and fin <= h.hora_cierre for h in franjas)


def _tarifa_de_bloque(tarifas: list[Tarifa], fecha: dt.date, inicio: dt.time) -> Tarifa | None:
    """Aplica la prioridad: especial > semanal. Devuelve la tarifa ganadora."""
    especial = next(
        (
            t
            for t in tarifas
            if t.activo and t.fecha_especial == fecha and t.hora_inicio <= inicio < t.hora_fin
        ),
        None,
    )
    if especial is not None:
        return especial
    dia = fecha.isoweekday()
    return next(
        (
            t
            for t in tarifas
            if t.activo and t.dia_semana == dia and t.hora_inicio <= inicio < t.hora_fin
        ),
        None,
    )


def _bloques_del_dia(franjas: list[HorarioOperacion]) -> list[tuple[dt.time, dt.time]]:
    bloques: list[tuple[dt.time, dt.time]] = []
    for franja in sorted(franjas, key=lambda h: h.hora_apertura):
        cursor = franja.hora_apertura
        while cursor < franja.hora_cierre:
            siguiente = (dt.datetime.combine(dt.date.min, cursor) + dt.timedelta(hours=1)).time()
            if siguiente > franja.hora_cierre:
                break
            bloques.append((cursor, siguiente))
            cursor = siguiente
    return bloques


def tarifar_fecha(cancha: Cancha, fecha: dt.date) -> list[Bloque]:
    """Vista previa: todos los bloques del día con su precio (T3.8)."""
    franjas = _franjas_del_dia(cancha, fecha)
    if not franjas:
        return []

    tarifas = list(cancha.tarifas.all())
    precio_base = Decimal(cancha.precio_base)

    resultado: list[Bloque] = []
    for inicio, fin in _bloques_del_dia(franjas):
        tarifa = _tarifa_de_bloque(tarifas, fecha, inicio)
        if tarifa is not None:
            resultado.append(
                Bloque(
                    hora_inicio=inicio,
                    hora_fin=fin,
                    precio=Decimal(tarifa.precio_hora),
                    origen=ORIGEN_ESPECIAL if tarifa.es_especial else ORIGEN_SEMANAL,
                    tarifa_id=tarifa.pk,
                )
            )
        else:
            resultado.append(
                Bloque(hora_inicio=inicio, hora_fin=fin, precio=precio_base, origen=ORIGEN_BASE)
            )
    return resultado


def calcular_precio(
    cancha: Cancha, fecha: dt.date, hora_inicio: dt.time, hora_fin: dt.time
) -> tuple[Decimal, list[Bloque]]:
    """Precio total de una reserva, sumando el valor de cada bloque de 60 min.

    Lanza `BusinessRuleViolation` si:
    - el rango no está alineado o su duración no es múltiplo de 60 (R4);
    - algún bloque cae fuera de las franjas de operación (R10).
    """
    assert_valid_booking_range(hora_inicio, hora_fin)

    franjas = _franjas_del_dia(cancha, fecha)
    if not franjas:
        raise BusinessRuleViolation(
            "La cancha no tiene horario de operación configurado para ese día.",
            code=FUERA_DE_HORARIO,
            errors={"fecha": fecha.isoformat()},
        )

    por_bloque = {b.hora_inicio: b for b in tarifar_fecha(cancha, fecha)}

    cursor = dt.datetime.combine(dt.date.min, hora_inicio)
    limite = dt.datetime.combine(dt.date.min, hora_fin)
    seleccionados: list[Bloque] = []
    while cursor < limite:
        siguiente = cursor + dt.timedelta(hours=1)
        bloque = por_bloque.get(cursor.time())
        if bloque is None or not _dentro_de_franja(franjas, cursor.time(), siguiente.time()):
            raise BusinessRuleViolation(
                f"El rango solicitado incluye un bloque fuera de horario ({cursor:%H:%M}).",
                code=FUERA_DE_HORARIO,
                errors={"hora_inicio": str(hora_inicio), "hora_fin": str(hora_fin)},
            )
        seleccionados.append(bloque)
        cursor = siguiente

    total = sum((b.precio for b in seleccionados), Decimal("0.00"))
    return total, seleccionados


__all__ = [
    "Bloque",
    "ORIGEN_BASE",
    "ORIGEN_SEMANAL",
    "ORIGEN_ESPECIAL",
    "tarifar_fecha",
    "calcular_precio",
]
