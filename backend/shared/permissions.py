"""Permisos compartidos por rol (T2.6 / T3).

`IsFieldAdmin` es la frontera de aislamiento del panel: un administrador solo
opera sobre **su** cancha (relación 1:1). La cancha se resuelve mediante
`fields.services` y queda en `request.cancha` para que las vistas no repitan la
consulta ni puedan elegir otra.

Mapeo de errores:

| Situación                        | Respuesta                          |
|----------------------------------|------------------------------------|
| Sin token / token inválido       | `401` (lo emite el autenticador)   |
| Autenticado pero no administrador| `403 rol_requerido`               |
| Administrador sin cancha         | `403 admin_sin_cancha`             |
| Administrador con su cancha      | `200` con `request.cancha` (1:1)   |
"""

from __future__ import annotations

from modules.fields import services as fields_services
from modules.users_auth.models import Rol
from rest_framework.permissions import BasePermission

from shared.exceptions import ADMIN_SIN_CANCHA, ROL_REQUERIDO, ForbiddenError


def get_usuario(request):
    usuario = getattr(request, "user", None)
    if usuario is not None and getattr(usuario, "is_authenticated", False):
        return usuario
    return None


class IsFieldAdmin(BasePermission):
    """Administrador activo con su cancha asignada (1:1)."""

    message = "Se requiere rol administrador."

    def has_permission(self, request, view) -> bool:
        usuario = get_usuario(request)
        if usuario is None:
            # Sin usuario: deja que DRF responda 401 (con WWW-Authenticate).
            return False

        if usuario.rol != Rol.ADMINISTRADOR or not usuario.activo:
            raise ForbiddenError("La operación requiere el rol administrador.", code=ROL_REQUERIDO)

        cancha = fields_services.get_cancha_by_admin(usuario)
        if cancha is None:
            raise ForbiddenError(
                "El administrador no tiene una cancha asignada.", code=ADMIN_SIN_CANCHA
            )

        request.cancha = cancha
        return True


class IsCliente(BasePermission):
    message = "Se requiere rol cliente."

    def has_permission(self, request, view) -> bool:
        usuario = get_usuario(request)
        if usuario is None:
            return False
        if usuario.rol != Rol.CLIENTE:
            raise ForbiddenError("La operación requiere el rol cliente.", code="rol_requerido")
        return True


__all__ = ["IsFieldAdmin", "IsCliente"]
