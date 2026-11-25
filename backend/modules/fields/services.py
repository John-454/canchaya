"""Servicios públicos del módulo `fields` (T3.1).

Otros módulos (p. ej. `shared.permissions` o `finance`) **no** importan
`modules.fields.models`; usan estas funciones.

Referencia rápida de reglas:
- 1:1 admin↔cancha: `canchas.id_administrador` es UNIQUE.
- Imagen principal única: índice único parcial (BD) + desmarcado transaccional.
- Solapes de horarios/tarifas: `ExclusionConstraint` en BD (R2); aquí se
  traducen a `409 horario_solapado` / `409 tarifa_solapada`.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction
from shared.exceptions import (
    HORARIO_SOLAPADO,
    TARIFA_SOLAPADA,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from shared.validators import assert_aligned, duration_minutes

from modules.fields.models import Cancha, HorarioOperacion, ImagenCancha, Tarifa


# ---------------------------------------------------------------------------
# Cancha (1:1)
# ---------------------------------------------------------------------------
def get_cancha_by_admin(usuario) -> Cancha | None:
    """Cancha del administrador autenticado (relación 1:1)."""
    if usuario is None or not getattr(usuario, "pk", None):
        return None
    return Cancha.objects.filter(id_administrador_id=usuario.pk).first()


def get_cancha(cancha_id: int) -> Cancha:
    cancha = Cancha.objects.filter(pk=cancha_id).first()
    if cancha is None:
        raise NotFoundError("La cancha no existe.")
    return cancha


@transaction.atomic
def update_mi_cancha(cancha: Cancha, datos: dict) -> Cancha:
    campos = {"nombre", "direccion", "zona", "descripcion", "precio_base", "estado"}
    cambios = [c for c in datos if c in campos]
    for campo in cambios:
        setattr(cancha, campo, datos[campo])
    if cambios:
        cancha.save(update_fields=cambios)
    return cancha


# ---------------------------------------------------------------------------
# Imágenes
# ---------------------------------------------------------------------------
def list_images(cancha: Cancha):
    return cancha.imagenes.all()


@transaction.atomic
def add_image(
    cancha: Cancha, *, url_imagen: str, descripcion: str = "", principal: bool = False
) -> ImagenCancha:
    es_primera = not cancha.imagenes.exists()
    if principal or es_primera:
        cancha.imagenes.filter(imagen_principal=True).update(imagen_principal=False)
        principal = True
    return ImagenCancha.objects.create(
        id_cancha=cancha,
        url_imagen=url_imagen,
        descripcion=descripcion or "",
        imagen_principal=principal,
    )


@transaction.atomic
def set_imagen_principal(cancha: Cancha, imagen_id: int) -> ImagenCancha:
    imagen = _get_imagen(cancha, imagen_id)
    cancha.imagenes.exclude(pk=imagen.pk).update(imagen_principal=False)
    if not imagen.imagen_principal:
        imagen.imagen_principal = True
        imagen.save(update_fields=["imagen_principal"])
    return imagen


@transaction.atomic
def delete_image(cancha: Cancha, imagen_id: int) -> None:
    """Elimina la imagen; si era la principal, promueve la más antigua (R9)."""
    imagen = _get_imagen(cancha, imagen_id)
    era_principal = imagen.imagen_principal
    imagen.delete()
    if era_principal:
        siguiente = cancha.imagenes.order_by("fecha_creacion", "pk").first()
        if siguiente is not None:
            siguiente.imagen_principal = True
            siguiente.save(update_fields=["imagen_principal"])


def _get_imagen(cancha: Cancha, imagen_id: int) -> ImagenCancha:
    # Filtrado por cancha: un id de otra cancha devuelve 404 (no filtra existencia).
    imagen = cancha.imagenes.filter(pk=imagen_id).first()
    if imagen is None:
        raise NotFoundError("La imagen no existe en tu cancha.")
    return imagen


get_imagen = _get_imagen


# ---------------------------------------------------------------------------
# Horarios
# ---------------------------------------------------------------------------
def list_schedules(cancha: Cancha):
    return cancha.horarios.all()


def _validar_rango_horario(cancha: Cancha, datos: dict) -> None:
    assert_aligned(datos["hora_apertura"], "hora_apertura")
    assert_aligned(datos["hora_cierre"], "hora_cierre")
    if duration_minutes(datos["hora_apertura"], datos["hora_cierre"]) <= 0:
        raise ValidationError(
            "El cierre debe ser posterior a la apertura.",
            code="rango_invalido",
            errors={"hora_cierre": "debe ser mayor que hora_apertura"},
        )


@transaction.atomic
def add_schedule(cancha: Cancha, datos: dict) -> HorarioOperacion:
    _validar_rango_horario(cancha, datos)
    try:
        return HorarioOperacion.objects.create(id_cancha=cancha, **datos)
    except IntegrityError as exc:
        raise ConflictError(
            "La franja se solapa con otra franja activa del mismo día.",
            code=HORARIO_SOLAPADO,
        ) from exc


@transaction.atomic
def update_schedule(cancha: Cancha, horario_id: int, datos: dict) -> HorarioOperacion:
    horario = cancha.horarios.filter(pk=horario_id).first()
    if horario is None:
        raise NotFoundError("El horario no existe en tu cancha.")
    for campo in ("dia_semana", "hora_apertura", "hora_cierre", "activo"):
        if campo in datos:
            setattr(horario, campo, datos[campo])
    _validar_rango_horario(
        cancha, {"hora_apertura": horario.hora_apertura, "hora_cierre": horario.hora_cierre}
    )
    try:
        horario.save()
    except IntegrityError as exc:
        raise ConflictError(
            "La franja se solapa con otra franja activa del mismo día.",
            code=HORARIO_SOLAPADO,
        ) from exc
    return horario


@transaction.atomic
def delete_schedule(cancha: Cancha, horario_id: int) -> None:
    horario = cancha.horarios.filter(pk=horario_id).first()
    if horario is None:
        raise NotFoundError("El horario no existe en tu cancha.")
    horario.delete()


# ---------------------------------------------------------------------------
# Tarifas
# ---------------------------------------------------------------------------
def list_rates(cancha: Cancha):
    return cancha.tarifas.all()


def _validar_tarifa(datos: dict) -> None:
    inicio = datos.get("hora_inicio")
    fin = datos.get("hora_fin")
    if inicio is not None:
        assert_aligned(inicio, "hora_inicio")
    if fin is not None:
        assert_aligned(fin, "hora_fin")
    if inicio is not None and fin is not None and duration_minutes(inicio, fin) <= 0:
        raise ValidationError(
            "hora_fin debe ser posterior a hora_inicio.",
            code="rango_invalido",
            errors={"hora_fin": "debe ser mayor que hora_inicio"},
        )
    if "precio_hora" in datos and Decimal(datos["precio_hora"]) <= 0:
        raise ValidationError(
            "El precio por hora debe ser mayor que cero.",
            code="precio_invalido",
            errors={"precio_hora": "debe ser > 0"},
        )


@transaction.atomic
def add_rate(cancha: Cancha, datos: dict) -> Tarifa:
    _validar_tarifa(datos)
    try:
        return Tarifa.objects.create(id_cancha=cancha, **datos)
    except IntegrityError as exc:
        raise _conflicto_tarifa(exc) from exc


@transaction.atomic
def update_rate(cancha: Cancha, tarifa_id: int, datos: dict) -> Tarifa:
    tarifa = cancha.tarifas.filter(pk=tarifa_id).first()
    if tarifa is None:
        raise NotFoundError("La tarifa no existe en tu cancha.")
    for campo in (
        "dia_semana",
        "fecha_especial",
        "hora_inicio",
        "hora_fin",
        "precio_hora",
        "activo",
    ):
        if campo in datos:
            setattr(tarifa, campo, datos[campo])
    _validar_tarifa(
        {
            "hora_inicio": tarifa.hora_inicio,
            "hora_fin": tarifa.hora_fin,
            "precio_hora": tarifa.precio_hora,
        }
    )
    try:
        tarifa.save()
    except IntegrityError as exc:
        raise _conflicto_tarifa(exc) from exc
    return tarifa


@transaction.atomic
def delete_rate(cancha: Cancha, tarifa_id: int) -> None:
    tarifa = cancha.tarifas.filter(pk=tarifa_id).first()
    if tarifa is None:
        raise NotFoundError("La tarifa no existe en tu cancha.")
    tarifa.delete()


def _conflicto_tarifa(exc: IntegrityError) -> ConflictError:
    texto = str(exc).lower()
    if "solape" in texto or "exclude" in texto:
        return ConflictError("La tarifa se solapa con otra tarifa activa.", code=TARIFA_SOLAPADA)
    return ConflictError("Los datos de la tarifa no son válidos.", code="tarifa_invalida")


__all__ = [
    "Cancha",
    "get_cancha",
    "get_cancha_by_admin",
    "update_mi_cancha",
    "list_images",
    "add_image",
    "set_imagen_principal",
    "get_imagen",
    "delete_image",
    "list_schedules",
    "add_schedule",
    "update_schedule",
    "delete_schedule",
    "list_rates",
    "add_rate",
    "update_rate",
    "delete_rate",
]
