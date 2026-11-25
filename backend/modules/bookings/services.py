"""Servicios del módulo `bookings` (T4.1 – T4.3).

Responsabilidades:

- **Expiración automática** a `Finalizada` (R7: comparación en hora local del
  negocio, `America/Bogota`).
- **Máquina de estados** de la reserva (Pendiente → Confirmada → Finalizada /
  Cancelada) con errores tipados.
- **Pago presencial** coherente (`Pagado` ⇔ `fecha_pago`).
- **Creación** de reservas con `precio_total` calculado por el `PricingEngine`
  (congelado) y `codigo_reserva` único con reintento acotado (R5).
- Captura de la `ExclusionConstraint` de solapes (R2) → `409 horario_no_disponible`.

Frontera: `finance` consume estas funciones; no importa `bookings.models`.
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from shared.dates import now_in_tz
from shared.exceptions import (
    ESTADO_INVALIDO,
    HORARIO_NO_DISPONIBLE,
    ConflictError,
    NotFoundError,
    ValidationError,
)

from modules.bookings.models import ESTADOS_BLOQUEANTES, EstadoPago, EstadoReserva, Reserva
from modules.fields.models import Cancha
from modules.fields.services_pricing import calcular_precio
from modules.users_auth import services as users_services

INTENTOS_CODIGO = 5
ALFABETO_CODIGO = string.ascii_uppercase + string.digits


# ---------------------------------------------------------------------------
# Código de reserva (R5): CY-YYMMDD-XXXX
# ---------------------------------------------------------------------------
def generar_codigo_reserva(fecha) -> str:
    sufijo = "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(4))
    return f"CY-{fecha:%y%m%d}-{sufijo}"


# ---------------------------------------------------------------------------
# Expiración a Finalizada
# ---------------------------------------------------------------------------
def expire_confirmed_bookings(cancha: Cancha | None = None) -> int:
    """Marca como `Finalizada` las reservas `Confirmada` ya vencidas.

    R7: se compara `fecha_reserva + hora_fin` contra "ahora" **en la hora local
    del negocio**, no con la hora del contenedor. Se evalúa antes de responder
    consultas de reservas o métricas.
    """
    ahora = now_in_tz()
    limite = ahora.date()
    qs = Reserva.objects.filter(estado_reserva=EstadoReserva.CONFIRMADA, fecha_reserva__lte=limite)
    if cancha is not None:
        qs = qs.filter(id_cancha=cancha)

    vencidas: list[int] = []
    for reserva in qs.only("id_reserva", "fecha_reserva", "hora_fin"):
        fin = timezone.make_aware(
            timezone.datetime.combine(reserva.fecha_reserva, reserva.hora_fin),
            timezone.get_current_timezone(),
        )
        if fin < ahora:
            vencidas.append(reserva.pk)

    if not vencidas:
        return 0
    return Reserva.objects.filter(pk__in=vencidas).update(estado_reserva=EstadoReserva.FINALIZADA)


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------
def get_admin_booking(cancha: Cancha, reserva_id: int) -> Reserva:
    reserva = Reserva.objects.filter(pk=reserva_id, id_cancha=cancha).first()
    if reserva is None:
        raise NotFoundError("La reserva no existe en tu cancha.")
    return reserva


def list_admin_bookings(cancha: Cancha, filtros: dict) -> QuerySet:
    """Reservas de la cancha con los filtros del panel (T4.4)."""
    qs = Reserva.objects.filter(id_cancha=cancha).select_related("id_cliente")
    if filtros.get("fecha"):
        qs = qs.filter(fecha_reserva=filtros["fecha"])
    if filtros.get("estado_reserva"):
        qs = qs.filter(estado_reserva=filtros["estado_reserva"])
    if filtros.get("estado_pago"):
        qs = qs.filter(estado_pago=filtros["estado_pago"])
    if filtros.get("cliente"):
        texto = filtros["cliente"]
        qs = qs.filter(
            Q(nombre_cliente__icontains=texto)
            | Q(correo_cliente__icontains=texto)
            | Q(telefono_cliente__icontains=texto)
        )
    if filtros.get("codigo_reserva"):
        qs = qs.filter(codigo_reserva__icontains=filtros["codigo_reserva"])
    return qs.order_by("-fecha_reserva", "-hora_inicio")


# ---------------------------------------------------------------------------
# Creación (usada por la Iteración 5 del cliente y por pruebas)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DatosReserva:
    cancha: Cancha
    cliente_id: int
    fecha_reserva: object
    hora_inicio: object
    hora_fin: object
    observaciones: str = ""


@transaction.atomic
def create_booking(datos: DatosReserva) -> Reserva:
    """Crea la reserva con precio calculado en backend y código único (R5)."""
    cliente = users_services.get_usuario(datos.cliente_id)
    if cliente is None:
        raise NotFoundError("El cliente no existe.")
    users_services.require_telefono(cliente)  # R1

    total, _bloques = calcular_precio(
        datos.cancha, datos.fecha_reserva, datos.hora_inicio, datos.hora_fin
    )

    for _intento in range(INTENTOS_CODIGO):
        codigo = generar_codigo_reserva(datos.fecha_reserva)
        try:
            with transaction.atomic():
                return Reserva.objects.create(
                    codigo_reserva=codigo,
                    id_cancha=datos.cancha,
                    id_cliente=cliente,
                    nombre_cliente=cliente.nombre,
                    correo_cliente=cliente.correo,
                    telefono_cliente=cliente.telefono,
                    fecha_reserva=datos.fecha_reserva,
                    hora_inicio=datos.hora_inicio,
                    hora_fin=datos.hora_fin,
                    precio_total=total,
                    estado_reserva=EstadoReserva.PENDIENTE,
                    estado_pago=EstadoPago.PENDIENTE,
                    observaciones=datos.observaciones,
                )
        except IntegrityError as exc:
            if "ex_reservas_no_solape" in str(exc):
                raise ConflictError(
                    "El horario ya está reservado.", code=HORARIO_NO_DISPONIBLE
                ) from exc
            if "codigo_reserva" in str(exc):
                continue  # colisión de código: se reintenta
            raise
    raise ConflictError(
        "No se pudo generar un código de reserva único.", code="codigo_no_disponible"
    )


# ---------------------------------------------------------------------------
# Máquina de estados
# ---------------------------------------------------------------------------
TRANSICIONES = {
    EstadoReserva.PENDIENTE: {EstadoReserva.CONFIRMADA, EstadoReserva.CANCELADA},
    EstadoReserva.CONFIRMADA: {EstadoReserva.CANCELADA, EstadoReserva.FINALIZADA},
    EstadoReserva.CANCELADA: set(),
    EstadoReserva.FINALIZADA: set(),
}


def _validar_transicion(reserva: Reserva, destino: str) -> None:
    permitidos = TRANSICIONES.get(reserva.estado_reserva, set())
    if destino not in permitidos:
        raise ConflictError(
            f"No se puede pasar de '{reserva.estado_reserva}' a '{destino}'.",
            code=ESTADO_INVALIDO,
            errors={"estado_actual": reserva.estado_reserva},
        )


@transaction.atomic
def approve(cancha: Cancha, reserva_id: int) -> Reserva:
    reserva = get_admin_booking(cancha, reserva_id)
    expire_confirmed_bookings(cancha)
    reserva.refresh_from_db()
    _validar_transicion(reserva, EstadoReserva.CONFIRMADA)
    try:
        with transaction.atomic():
            reserva.estado_reserva = EstadoReserva.CONFIRMADA
            reserva.save(update_fields=["estado_reserva"])
    except IntegrityError as exc:
        raise ConflictError(
            "El horario se ocupó con otra reserva mientras se aprobaba.",
            code=HORARIO_NO_DISPONIBLE,
        ) from exc
    return reserva


@transaction.atomic
def cancel(cancha: Cancha, reserva_id: int, motivo: str | None = None) -> Reserva:
    reserva = get_admin_booking(cancha, reserva_id)
    expire_confirmed_bookings(cancha)
    reserva.refresh_from_db()
    _validar_transicion(reserva, EstadoReserva.CANCELADA)
    reserva.estado_reserva = EstadoReserva.CANCELADA
    campos = ["estado_reserva"]
    if motivo:
        nota = f"Cancelada por el administrador: {motivo.strip()}"
        reserva.observaciones = f"{reserva.observaciones}\n{nota}".strip()
        campos.append("observaciones")
    reserva.save(update_fields=campos)
    return reserva


@transaction.atomic
def mark_paid(cancha: Cancha, reserva_id: int) -> Reserva:
    """Pago presencial: `Pagado` + `fecha_pago = now` (coherencia §3.3)."""
    reserva = get_admin_booking(cancha, reserva_id)
    if reserva.estado_reserva == EstadoReserva.CANCELADA:
        raise ConflictError(
            "No se puede marcar como pagada una reserva cancelada.",
            code=ESTADO_INVALIDO,
            errors={"estado_reserva": reserva.estado_reserva},
        )
    if reserva.estado_pago == EstadoPago.PAGADO:
        raise ConflictError("La reserva ya está marcada como pagada.", code="reserva_ya_pagada")
    reserva.estado_pago = EstadoPago.PAGADO
    reserva.fecha_pago = timezone.now()
    reserva.save(update_fields=["estado_pago", "fecha_pago"])
    return reserva


def validar_filtros(filtros: dict) -> None:
    if filtros.get("estado_reserva") and filtros["estado_reserva"] not in EstadoReserva.values:
        raise ValidationError(
            "estado_reserva inválido.",
            errors={"estado_reserva": sorted(EstadoReserva.values)},
        )
    if filtros.get("estado_pago") and filtros["estado_pago"] not in EstadoPago.values:
        raise ValidationError(
            "estado_pago inválido.", errors={"estado_pago": sorted(EstadoPago.values)}
        )


__all__ = [
    "Reserva",
    "EstadoReserva",
    "EstadoPago",
    "ESTADOS_BLOQUEANTES",
    "DatosReserva",
    "generar_codigo_reserva",
    "expire_confirmed_bookings",
    "create_booking",
    "approve",
    "cancel",
    "mark_paid",
    "get_admin_booking",
    "list_admin_bookings",
    "validar_filtros",
]
