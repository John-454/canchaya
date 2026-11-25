"""Manejador de excepciones común a todas las vistas DRF."""

from __future__ import annotations

import logging

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from shared.exceptions import TELEFONO_REQUERIDO, ConflictError, DomainError  # noqa: F401

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    if isinstance(exc, DomainError):
        payload = {"code": exc.code, "detail": exc.detail}
        if exc.errors:
            payload["errors"] = exc.errors
        return Response(payload, status=exc.status_code)

    if isinstance(exc, IntegrityError):
        # Las exclusion constraints de PostgreSQL llegan aquí. El módulo que
        # conoce el dominio debería atraparlas antes; esto es la última barrera.
        logger.warning("IntegrityError no capturada: %s", exc)
        return Response(
            {"code": "conflicto_integridad", "detail": "Violación de integridad de datos."},
            status=status.HTTP_409_CONFLICT,
        )

    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "code": _codigo(exc),
            "detail": _flatten(response.data),
        }
    return response


def _codigo(exc) -> str:
    """Código estable: prioriza el atributo `code` propio de la excepción."""
    codigo = getattr(exc, "code", None)
    if codigo:
        return str(codigo)
    detalle = getattr(exc, "detail", None)
    if hasattr(detalle, "code"):
        return str(detalle.code)
    return getattr(exc, "default_code", "error")


def _reto(exc) -> str:
    """Cabecera `WWW-Authenticate` mínima para que DRF emita 401 de verdad."""
    return 'Bearer realm="api"'


def conflict(detail: str, code: str) -> ConflictError:
    return ConflictError(detail, code=code)


def _flatten(data):
    if isinstance(data, dict) and len(data) == 1 and "detail" in data:
        return str(data["detail"])
    return data
