"""Autenticación DRF por JWT de Supabase (T2.2).

Flujo:
1. Extrae el token del header `Authorization: Bearer <jwt>`.
2. Lo valida con `shared.auth.supabase.verificar_token`.
3. Busca el perfil en `usuarios` por `supabase_uid` (o lo vincula por correo si
   el perfil fue aprovisionado antes del primer login).
4. Rechaza cuentas desactivadas o tokens expirados/ inválidos con 401/403 tipados.
"""

from __future__ import annotations

from modules.users_auth import services as users_services
from rest_framework import authentication, exceptions

from shared.auth import supabase
from shared.exceptions import CUENTA_DESACTIVADA, PERFIL_NO_SINCRONIZADO, ForbiddenError


class AutenticacionFallida(exceptions.AuthenticationFailed):
    """401 real: fuerza la cabecera `WWW-Authenticate` (si no, DRF lo vuelve 403)."""

    def __init__(self, detalle: str, code: str = "token_invalido") -> None:
        super().__init__(detalle, code=code)
        self.auth_header = 'Bearer realm="api"'


class CredencialesInvalidas(AutenticacionFallida):
    pass


class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    """Autentica peticiones con la firma JWT de Supabase Auth."""

    keyword = "Bearer"

    def authenticate(self, request):
        encabezado = authentication.get_authorization_header(request).split()
        if not encabezado:
            return None
        if len(encabezado) != 2 or encabezado[0].lower() != self.keyword.lower().encode():
            raise CredencialesInvalidas(
                "El encabezado Authorization debe ser 'Bearer <token>'.",
                code="encabezado_invalido",
            )

        token = encabezado[1].decode("utf-8", errors="strict")
        try:
            claims = supabase.verificar_token(token)
        except supabase.TokenExpirado as exc:
            raise CredencialesInvalidas(exc.detalle, code=exc.code) from exc
        except supabase.TokenInvalido as exc:
            raise CredencialesInvalidas(exc.detalle, code=exc.code) from exc
        except supabase.ConfiguracionAusente as exc:
            raise CredencialesInvalidas(exc.detalle, code=exc.code) from exc

        usuario = users_services.resolver_usuario_autenticado(claims)
        if usuario is None:
            raise CredencialesInvalidas(
                "El perfil no está sincronizado. Llama a /api/v1/auth/sync/.",
                code=PERFIL_NO_SINCRONIZADO,
            )
        if not usuario.activo:
            raise exceptions.PermissionDenied(
                detail="La cuenta está desactivada.",
                code=CUENTA_DESACTIVADA,
            )

        request.supabase_claims = claims.crudo
        return usuario, token

    def authenticate_header(self, request) -> str:
        return 'Bearer realm="api"'


__all__ = ["SupabaseJWTAuthentication", "CredencialesInvalidas", "ForbiddenError"]
