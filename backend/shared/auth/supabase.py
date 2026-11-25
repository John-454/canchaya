"""Validación de tokens JWT emitidos por Supabase Auth (T2.1).

Soporte de algoritmos:
- **ES256 / ES384 / ES512** (lo que emiten los proyectos nuevos de Supabase,
  claves EC en el JWKS) → verificación por clave pública del JWKS.
- **RS256** (proyectos con claves RSA) → idem.
- **HS256 (legacy)** → `SUPABASE_JWT_SECRET`.

El JWKS se descarga de `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, se cachea
con TTL y se selecciona la clave por `kid`. Se valida `exp`, `aud`
(`authenticated`) e `iss` (`{SUPABASE_URL}/auth/v1`).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import jwt
import requests
from django.conf import settings

# Algoritmos asimétricos soportados (se resuelven con el JWKS).
ALGORITMOS_ASIMETRICOS = {"ES256", "ES384", "ES512", "RS256", "RS384", "RS512"}
ALGORITMO_SIMETRICO = "HS256"
AUDIENCIA = "authenticated"


class SupabaseTokenError(Exception):
    """Error base de validación de token."""

    code = "token_invalido"

    def __init__(self, detalle: str) -> None:
        self.detalle = detalle
        super().__init__(detalle)


class TokenExpirado(SupabaseTokenError):
    code = "token_expirado"


class TokenInvalido(SupabaseTokenError):
    code = "token_invalido"


class ConfiguracionAusente(SupabaseTokenError):
    code = "auth_no_configurada"


@dataclass(frozen=True)
class ClaimsToken:
    """Claims relevantes del token de Supabase."""

    sub: str
    correo: str
    nombre: str
    crudo: dict


class _CacheJWKS:
    """Cache en memoria de las claves públicas (con TTL)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._claves: dict[str, jwt.algorithms.RSAAlgorithm | None] = {}
        self._expira_en = 0.0
        self._kid_desconocido_refresh = 0.0
        self._ultimo_refresco = 0.0

    def obtener(self, kid: str | None) -> object | None:
        ahora = time.monotonic()
        with self._lock:
            if self._claves and ahora < self._expira_en:
                if kid is None or kid in self._claves:
                    return self._claves.get(kid) if kid else next(iter(self._claves.values()))
            # `_refrescar()` puede repoblar el cache de forma externa (tests) y
            # no debe repoblarlo indefinidamente: se marca la hora del intento.
            self._ultimo_refresco = ahora
            self._refrescar()
            if kid is None:
                return next(iter(self._claves.values()), None)
            return self._claves.get(kid)

    def refrescar_si_kid_desconocido(self, kid: str | None, ventana: float = 5.0) -> object | None:
        """Refresca ante un `kid` desconocido, pero sin huracán de peticiones.

        Si ya se refrescó hace menos de `ventana` segundos, se devuelve `None`
        (la clave no existe realmente; evita bucles y martilleo al proveedor).
        """
        ahora = time.monotonic()
        with self._lock:
            if ahora - self._ultimo_refresco < ventana:
                return None
        self.invalidar()
        return self.obtener(kid)

    def _refrescar(self) -> None:
        url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        try:
            respuesta = requests.get(url, timeout=5)
            respuesta.raise_for_status()
            cuerpo = respuesta.json()
        except requests.RequestException as exc:
            raise ConfiguracionAusente(f"No se pudo obtener el JWKS de Supabase: {exc}") from exc

        claves: dict[str, object] = {}
        for jwk in cuerpo.get("keys", []):
            kid = jwk.get("kid")
            if not kid:
                continue
            # `jwt.PyJWK` acepta el dict del JWK y expone `.key` (clave pública).
            try:
                claves[kid] = jwt.PyJWK(jwk).key
            except jwt.PyJWTError:
                continue
        self._claves = claves
        self._expira_en = time.monotonic() + settings.SUPABASE_JWKS_CACHE_TTL
        self._ultimo_refresco = time.monotonic()

    def invalidar(self) -> None:
        with self._lock:
            self._claves = {}
            self._expira_en = 0.0


_cache = _CacheJWKS()


def _decodificar(token: str, key: object, algoritmos: list[str]) -> dict:
    kwargs: dict = {}
    if settings.SUPABASE_URL:
        # `issuer` solo se valida si se pasa como kwarg (no como opción) y
        # `verify_iss` debe estar activo.
        kwargs["issuer"] = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1"
    try:
        return jwt.decode(
            token,
            key,
            algorithms=algoritmos,
            audience=AUDIENCIA,
            options={
                "require": ["exp", "sub", "aud"],
                "verify_iss": bool(settings.SUPABASE_URL),
            },
            **kwargs,
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpirado("El token de sesión ha expirado.") from exc
    except jwt.InvalidIssuerError as exc:
        raise TokenInvalido("Emisor del token no reconocido.") from exc
    except jwt.InvalidAudienceError as exc:
        raise TokenInvalido("Audiencia del token no reconocida.") from exc
    except jwt.PyJWTError as exc:
        raise TokenInvalido(f"Token inválido: {exc}") from exc


def _claims(payload: dict) -> ClaimsToken:
    sub = payload.get("sub")
    if not sub:
        raise TokenInvalido("El token no identifica al usuario (sin 'sub').")
    metadata = payload.get("user_metadata") or {}
    correo = (metadata.get("email") or payload.get("email") or "").strip().lower()
    nombre = (
        metadata.get("full_name")
        or metadata.get("name")
        or (correo.split("@")[0] if correo else "")
    )
    return ClaimsToken(sub=str(sub), correo=correo, nombre=str(nombre or ""), crudo=payload)


def verificar_token(token: str) -> ClaimsToken:
    """Valida el token y devuelve los claims normalizados.

    Estrategia: se respeta el `alg` del encabezado.
    - `HS256` → `SUPABASE_JWT_SECRET` (proyectos legacy).
    - `ES256/384/512`, `RS256/384/512` → clave pública del JWKS de `SUPABASE_URL`.
    Supabase puede rotar entre familias sin cambiar la app.
    """
    if not token:
        raise TokenInvalido("Falta el token de autenticación.")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise TokenInvalido("Encabezado del token ilegible.") from exc
    alg = header.get("alg", "")

    if alg == ALGORITMO_SIMETRICO:
        if not settings.SUPABASE_JWT_SECRET:
            raise ConfiguracionAusente("El proyecto no tiene configurado SUPABASE_JWT_SECRET.")
        payload = _decodificar(token, settings.SUPABASE_JWT_SECRET, [ALGORITMO_SIMETRICO])
    elif alg in ALGORITMOS_ASIMETRICOS:
        if not settings.SUPABASE_URL:
            raise ConfiguracionAusente("El proyecto no tiene configurado SUPABASE_URL.")
        kid = header.get("kid")
        clave = _cache.obtener(kid)
        if clave is None:
            # Rotación de claves: se refresca una vez, con ventana anti-martilleo.
            clave = _cache.refrescar_si_kid_desconocido(kid)
        if clave is None:
            raise TokenInvalido(
                f"No se encontró la clave pública del token (alg={alg}, kid={kid})."
            )
        payload = _decodificar(token, clave, [alg])
    else:
        raise TokenInvalido(f"Algoritmo de firma no soportado: {alg or 'desconocido'}.")

    return _claims(payload)


def limpiar_cache_jwks() -> None:
    """Para tests: fuerza a releer el JWKS en la próxima validación."""
    _cache.invalidar()
