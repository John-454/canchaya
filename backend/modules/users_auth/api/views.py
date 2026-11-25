"""Vistas del módulo users_auth (§5.1 — T2.3, T2.4, T2.5)."""

from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from shared.api_base import PublicAPIView
from shared.auth.authentication import CredencialesInvalidas
from shared.auth.supabase import (
    SupabaseTokenError,
    verificar_token,
)

from modules.users_auth import services
from modules.users_auth.api.serializers import PerfilUpdateSerializer, UsuarioSerializer


class SyncView(PublicAPIView):
    """POST /api/v1/auth/sync/ — valida el token y crea/actualiza el perfil.

    Es público a nivel de DRF a propósito: el perfil puede **no existir
    todavía**, y aquí es justamente donde se crea (rol `cliente` por defecto).
    El token se valida obligatoriamente dentro de la vista.

    T6.1: limitado por IP (`auth_sync`, 20/min) para frenar la creación masiva
    de perfiles desde un token robado o un script.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_sync"

    def post(self, request):
        token = _extraer_token(request)
        try:
            claims = verificar_token(token)
        except SupabaseTokenError as exc:  # TokenExpirado / TokenInvalido / Config
            raise CredencialesInvalidas(exc.detalle, code=exc.code) from exc

        usuario, creado = services.sync_usuario(claims)
        if not usuario.activo:
            return Response(
                {"code": "cuenta_desactivada", "detail": "La cuenta está desactivada."},
                status=status.HTTP_403_FORBIDDEN,
            )

        datos = UsuarioSerializer(usuario).data
        datos["creado"] = creado
        return Response(datos, status=status.HTTP_200_OK)


class MeView(APIView):
    """GET / PATCH /api/v1/auth/me/ — perfil del usuario autenticado."""

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)

    def patch(self, request):
        serializer = PerfilUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = services.update_perfil(request.user, serializer.validated_data)
        return Response(UsuarioSerializer(usuario).data)


def _extraer_token(request) -> str:
    encabezado = request.headers.get("Authorization", "")
    partes = encabezado.split()
    if len(partes) != 2 or partes[0].lower() != "bearer":
        raise CredencialesInvalidas(
            "Se requiere el encabezado 'Authorization: Bearer <token>'.",
            code="encabezado_invalido",
        )
    return partes[1]
