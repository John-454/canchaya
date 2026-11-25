"""Consultas de solo lectura para `finance` (T4.8).

Frontera (R8): este módulo **no** importa `modules.bookings.models`; usa la
interfaz pública `bookings.services` y ejecuta agregaciones sobre el queryset
que ese servicio devuelve.

Reglas contables (§3.4):

- **Ingresos recibidos**: `precio_total` de reservas con
  `estado_reserva IN ('Confirmada','Finalizada')` **y** `estado_pago = 'Pagado'`.
- **Dinero pendiente**: idem con `estado_pago = 'Pendiente'`.
- `Cancelada` y `Pendiente` de aprobación **no** suman a ninguno de los dos.
- No se calculan gastos ni utilidad neta.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from shared.dates import custom_bounds, day_bounds, month_bounds, today_in_tz, week_bounds
from shared.exceptions import ValidationError

from modules.bookings.models import EstadoPago, EstadoReserva
from modules.bookings.services import Reserva

CERO = Decimal("0.00")

ESTADOS_CONTABLES = [EstadoReserva.CONFIRMADA, EstadoReserva.FINALIZADA]


def _base(cancha, inicio: dt.date | None = None, fin: dt.date | None = None):
    qs = Reserva.objects.filter(id_cancha=cancha, estado_reserva__in=ESTADOS_CONTABLES)
    if inicio is not None:
        qs = qs.filter(fecha_reserva__gte=inicio)
    if fin is not None:
        qs = qs.filter(fecha_reserva__lte=fin)
    return qs


def _suma(qs) -> Decimal:
    return qs.aggregate(
        total=Coalesce(
            Sum("precio_total"), CERO, output_field=DecimalField(max_digits=14, decimal_places=2)
        )
    )["total"]


def ingresos_recibidos(cancha, inicio=None, fin=None) -> Decimal:
    return _suma(_base(cancha, inicio, fin).filter(estado_pago=EstadoPago.PAGADO))


def dinero_pendiente(cancha, inicio=None, fin=None) -> Decimal:
    return _suma(_base(cancha, inicio, fin).filter(estado_pago=EstadoPago.PENDIENTE))


@dataclass(frozen=True)
class Rango:
    inicio: dt.date
    fin: dt.date
    etiqueta: str


def resolver_rango(period: str, start: str | None, end: str | None) -> Rango:
    """period: day | week | month | custom (fechas inclusivas)."""
    hoy = today_in_tz()
    if period == "day":
        return Rango(hoy, hoy, period)
    if period == "week":
        inicio, _ = week_bounds(hoy)
        return Rango(inicio.date(), inicio.date() + dt.timedelta(days=6), period)
    if period == "month":
        inicio, fin = month_bounds(hoy)
        return Rango(inicio.date(), (fin - dt.timedelta(days=1)).date(), period)
    if period == "custom":
        if not start or not end:
            raise ValidationError(
                "Para period=custom se requieren 'start' y 'end' (YYYY-MM-DD).",
                code="parametros_invalidos",
                errors={"start": "requerido", "end": "requerido"},
            )
        try:
            f_inicio = dt.date.fromisoformat(start)
            f_fin = dt.date.fromisoformat(end)
        except ValueError as exc:
            raise ValidationError("Fechas inválidas.", code="parametros_invalidos") from exc
        if f_inicio > f_fin:
            raise ValidationError(
                "start no puede ser posterior a end.", code="parametros_invalidos"
            )
        return Rango(f_inicio, f_fin, period)

    raise ValidationError(
        "period debe ser day, week, month o custom.",
        code="parametros_invalidos",
        errors={"period": ["day", "week", "month", "custom"]},
    )


# ---------------------------------------------------------------------------
# Resumen contable
# ---------------------------------------------------------------------------
def summary(cancha, rango: Rango) -> dict:
    base = _base(cancha, rango.inicio, rango.fin)
    recibidos_qs = base.filter(estado_pago=EstadoPago.PAGADO)
    pendientes_qs = base.filter(estado_pago=EstadoPago.PENDIENTE)

    por_dia = (
        base.values("fecha_reserva")
        .annotate(
            recibidos=Coalesce(
                Sum("precio_total", filter=Q(estado_pago=EstadoPago.PAGADO)),
                CERO,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            pendientes=Coalesce(
                Sum("precio_total", filter=Q(estado_pago=EstadoPago.PENDIENTE)),
                CERO,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            total=Count("id_reserva"),
        )
        .order_by("fecha_reserva")
    )

    return {
        "periodo": rango.etiqueta,
        "inicio": rango.inicio.isoformat(),
        "fin": rango.fin.isoformat(),
        "ingresos_recibidos": str(_suma(recibidos_qs)),
        "dinero_pendiente": str(_suma(pendientes_qs)),
        "total_reservas": base.count(),
        "reservas_pagadas": recibidos_qs.count(),
        "reservas_pendientes_pago": pendientes_qs.count(),
        "por_dia": [
            {
                "fecha": fila["fecha_reserva"].isoformat(),
                "ingresos_recibidos": str(fila["recibidos"]),
                "dinero_pendiente": str(fila["pendientes"]),
                "reservas": fila["total"],
            }
            for fila in por_dia
        ],
        "historial": [
            {
                "id_reserva": r.id_reserva,
                "codigo_reserva": r.codigo_reserva,
                "fecha_reserva": r.fecha_reserva.isoformat(),
                "hora_inicio": r.hora_inicio.strftime("%H:%M"),
                "hora_fin": r.hora_fin.strftime("%H:%M"),
                "nombre_cliente": r.nombre_cliente,
                "precio_total": str(r.precio_total),
                "estado_reserva": r.estado_reserva,
                "estado_pago": r.estado_pago,
                "fecha_pago": r.fecha_pago.isoformat() if r.fecha_pago else None,
            }
            for r in base.order_by("-fecha_reserva", "-hora_inicio")
        ],
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def kpis_dashboard(cancha) -> dict:
    hoy = today_in_tz()
    del_dia = Reserva.objects.filter(id_cancha=cancha, fecha_reserva=hoy)
    conteo = del_dia.aggregate(
        total=Count("id_reserva"),
        pendientes=Count("id_reserva", filter=Q(estado_reserva=EstadoReserva.PENDIENTE)),
        confirmadas=Count("id_reserva", filter=Q(estado_reserva=EstadoReserva.CONFIRMADA)),
        canceladas=Count("id_reserva", filter=Q(estado_reserva=EstadoReserva.CANCELADA)),
    )
    return {
        "reservas_hoy": conteo["total"],
        "pendientes_hoy": conteo["pendientes"],
        "confirmadas_hoy": conteo["confirmadas"],
        "canceladas_hoy": conteo["canceladas"],
        "por_aprobar": Reserva.objects.filter(
            id_cancha=cancha, estado_reserva=EstadoReserva.PENDIENTE, fecha_reserva__gte=hoy
        ).count(),
        "ingresos_recibidos": str(ingresos_recibidos(cancha)),
        "dinero_pendiente": str(dinero_pendiente(cancha)),
    }


def serie_actividad(cancha, dias: int = 30) -> list[dict]:
    hoy = today_in_tz()
    desde = hoy - dt.timedelta(days=dias - 1)
    filas = {
        f["fecha_reserva"]: f
        for f in Reserva.objects.filter(
            id_cancha=cancha, fecha_reserva__gte=desde, fecha_reserva__lte=hoy
        )
        .values("fecha_reserva")
        .annotate(total=Count("id_reserva"))
    }
    return [
        {
            "fecha": (desde + dt.timedelta(days=i)).isoformat(),
            "reservas": filas.get(desde + dt.timedelta(days=i), {}).get("total", 0),
        }
        for i in range(dias)
    ]


def serie_ingresos(cancha, meses: int = 6) -> list[dict]:
    hoy = today_in_tz()
    primero = hoy.replace(day=1)
    for _ in range(meses - 1):
        primero = (primero - dt.timedelta(days=1)).replace(day=1)
    filas = (
        _base(cancha, primero, hoy)
        .annotate(mes_trunc=TruncMonth("fecha_reserva"))
        .values("mes_trunc")
        .annotate(
            recibidos=Coalesce(
                Sum("precio_total", filter=Q(estado_pago=EstadoPago.PAGADO)),
                CERO,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .order_by("mes_trunc")
    )
    por_mes = {f["mes_trunc"].strftime("%Y-%m"): str(f["recibidos"]) for f in filas}
    resultado, cursor = [], primero
    while cursor <= hoy:
        clave = cursor.strftime("%Y-%m")
        resultado.append({"mes": clave, "ingresos_recibidos": por_mes.get(clave, "0.00")})
        cursor = (cursor + dt.timedelta(days=32)).replace(day=1)
    return resultado


def solicitudes_por_aprobar(cancha, limite: int = 5) -> list[dict]:
    hoy = today_in_tz()
    qs = Reserva.objects.filter(
        id_cancha=cancha, estado_reserva=EstadoReserva.PENDIENTE, fecha_reserva__gte=hoy
    ).order_by("fecha_reserva", "hora_inicio")[:limite]
    return [
        {
            "id_reserva": r.id_reserva,
            "codigo_reserva": r.codigo_reserva,
            "fecha_reserva": r.fecha_reserva.isoformat(),
            "hora_inicio": r.hora_inicio.strftime("%H:%M"),
            "hora_fin": r.hora_fin.strftime("%H:%M"),
            "nombre_cliente": r.nombre_cliente,
            "precio_total": str(r.precio_total),
        }
        for r in qs
    ]


def proximos_partidos(cancha, limite: int = 5) -> list[dict]:
    from django.utils import timezone

    ahora = timezone.localtime()
    qs = Reserva.objects.filter(
        id_cancha=cancha,
        estado_reserva=EstadoReserva.CONFIRMADA,
        fecha_reserva__gte=ahora.date(),
    ).order_by("fecha_reserva", "hora_inicio")[: limite * 3]
    resultado = []
    for r in qs:
        inicio = timezone.make_aware(
            timezone.datetime.combine(r.fecha_reserva, r.hora_inicio),
            timezone.get_current_timezone(),
        )
        if inicio >= ahora:
            resultado.append(
                {
                    "id_reserva": r.id_reserva,
                    "codigo_reserva": r.codigo_reserva,
                    "fecha_reserva": r.fecha_reserva.isoformat(),
                    "hora_inicio": r.hora_inicio.strftime("%H:%M"),
                    "hora_fin": r.hora_fin.strftime("%H:%M"),
                    "nombre_cliente": r.nombre_cliente,
                    "estado_pago": r.estado_pago,
                }
            )
        if len(resultado) == limite:
            break
    return resultado


__all__ = [
    "ingresos_recibidos",
    "dinero_pendiente",
    "resolver_rango",
    "summary",
    "kpis_dashboard",
    "serie_actividad",
    "serie_ingresos",
    "solicitudes_por_aprobar",
    "proximos_partidos",
    "Rango",
    "day_bounds",
    "week_bounds",
    "month_bounds",
    "custom_bounds",
]
