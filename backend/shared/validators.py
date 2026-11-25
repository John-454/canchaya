"""Validadores de dominio reutilizables (R4: alineación a bloques de 60 min)."""

from __future__ import annotations

import datetime as dt

from shared.exceptions import BLOQUE_NO_ALINEADO, DURACION_INVALIDA, BusinessRuleViolation


def is_aligned_on_the_hour(value: dt.time) -> bool:
    return value.minute == 0 and value.second == 0 and value.microsecond == 0


def is_aligned_time(value: dt.time) -> bool:
    """Alias legible para usar en tests y serializers."""
    return is_aligned_on_the_hour(value)


def assert_aligned(value: dt.time, campo: str = "hora") -> None:
    if not is_aligned_on_the_hour(value):
        raise BusinessRuleViolation(
            f"{campo} debe estar alineada a una hora en punto (HH:00).",
            code=BLOQUE_NO_ALINEADO,
            errors={campo: str(value)},
        )


def duration_minutes(hora_inicio: dt.time, hora_fin: dt.time) -> int:
    """Minutos entre dos horas del mismo día (positivo si fin > inicio)."""
    return (hora_fin.hour * 60 + hora_fin.minute) - (hora_inicio.hour * 60 + hora_inicio.minute)


def assert_valid_booking_range(hora_inicio: dt.time, hora_fin: dt.time) -> None:
    """Regla R4: inicio/fin en punto, duración >= 60 y múltiplo de 60."""
    assert_aligned(hora_inicio, "hora_inicio")
    assert_aligned(hora_fin, "hora_fin")
    minutos = duration_minutes(hora_inicio, hora_fin)
    if minutos < 60 or minutos % 60 != 0:
        raise BusinessRuleViolation(
            "La duración debe ser de al menos 1 hora y en bloques exactos de 60 minutos.",
            code=DURACION_INVALIDA,
            errors={"hora_inicio": str(hora_inicio), "hora_fin": str(hora_fin)},
        )


def blocks_of(hora_inicio: dt.time, hora_fin: dt.time):
    """Genera los bloques de 60 min que componen un rango alineado."""
    assert_valid_booking_range(hora_inicio, hora_fin)
    cursor = dt.datetime.combine(dt.date.min, hora_inicio)
    end = dt.datetime.combine(dt.date.min, hora_fin)
    while cursor < end:
        nxt = cursor + dt.timedelta(hours=1)
        yield cursor.time(), nxt.time()
        cursor = nxt
