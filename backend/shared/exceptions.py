"""Excepciones de dominio.

Todos los módulos lanzan estas excepciones; `shared.exceptions_handler` las traduce a
respuestas HTTP con un cuerpo estable `{"code": "...", "detail": "...", "errors": {...}}`.
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Error de negocio genérico (HTTP 400 por defecto)."""

    status_code = 400
    default_code = "domain_error"
    default_detail = "La operación no es válida."

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        errors: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.default_detail
        self.code = code or self.default_code
        self.errors = errors
        super().__init__(self.detail)


class ValidationError(DomainError):
    status_code = 400
    default_code = "datos_invalidos"
    default_detail = "Datos inválidos."


class ForbiddenError(DomainError):
    status_code = 403
    default_code = "prohibido"
    default_detail = "No tiene permisos para esta operación."


class NotFoundError(DomainError):
    status_code = 404
    default_code = "no_encontrado"
    default_detail = "El recurso no existe."


class ConflictError(DomainError):
    """Recursos en conflicto: solapes, estados inválidos, carreras."""

    status_code = 409
    default_code = "conflicto"
    default_detail = "La operación entra en conflicto con el estado actual."


class BusinessRuleViolation(DomainError):
    """Regla de negocio incumplida (mismo 400, pero semánticamente distinto)."""

    status_code = 400
    default_code = "regla_de_negocio"
    default_detail = "Se incumplió una regla de negocio."


# --- Códigos concretos usados por el dominio (evitan strings dispersos) ----
TELEFONO_REQUERIDO = "telefono_requerido"
FUERA_DE_HORARIO = "fuera_de_horario"
BLOQUE_NO_ALINEADO = "bloque_no_alineado"
DURACION_INVALIDA = "duracion_invalida"
HORARIO_SOLAPADO = "horario_solapado"
TARIFA_SOLAPADA = "tarifa_solapada"
HORARIO_NO_DISPONIBLE = "horario_no_disponible"
ESTADO_INVALIDO = "estado_invalido"
ADMIN_SIN_CANCHA = "admin_sin_cancha"
ROL_REQUERIDO = "rol_requerido"
PERFIL_NO_SINCRONIZADO = "perfil_no_sincronizado"
CUENTA_DESACTIVADA = "cuenta_desactivada"
