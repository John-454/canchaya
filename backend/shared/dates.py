"""Utilidades de fecha/hora ancladas a la zona horaria de negocio (America/Bogota)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from django.utils import timezone


def now_in_tz() -> dt.datetime:
    """Ahora, con tzinfo, en la zona horaria configurada."""
    return timezone.now().astimezone(timezone.get_current_timezone())


def today_in_tz() -> dt.date:
    return now_in_tz().date()


def day_bounds(fecha: dt.date) -> tuple[dt.datetime, dt.datetime]:
    tz = timezone.get_current_timezone()
    start = dt.datetime.combine(fecha, dt.time.min, tzinfo=tz)
    return start, start + dt.timedelta(days=1)


def week_bounds(fecha: dt.date) -> tuple[dt.datetime, dt.datetime]:
    """Semana ISO (lunes→lunes siguiente), en hora local."""
    monday = fecha - dt.timedelta(days=fecha.weekday())
    start, _ = day_bounds(monday)
    return start, start + dt.timedelta(days=7)


def month_bounds(fecha: dt.date) -> tuple[dt.datetime, dt.datetime]:
    first = fecha.replace(day=1)
    nxt = (first + dt.timedelta(days=32)).replace(day=1)
    start, _ = day_bounds(first)
    end, _ = day_bounds(nxt)
    return start, end


def custom_bounds(fecha_inicio: dt.date, fecha_fin: dt.date) -> tuple[dt.datetime, dt.datetime]:
    """Rango personalizado [inicio, fin] con `fecha_fin` inclusiva."""
    start, _ = day_bounds(fecha_inicio)
    _, end = day_bounds(fecha_fin)
    return start, end


@dataclass(frozen=True)
class Slot:
    """Bloque horario de 60 minutos. Las horas son `datetime.time` en punto."""

    inicio: dt.time
    fin: dt.time

    @property
    def clave(self) -> str:
        return f"{self.inicio:%H:%M}-{self.fin:%H:%M}"
