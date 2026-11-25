"""Helpers de test: claves RSA en memoria y tokens de Supabase firmados."""

from __future__ import annotations

import base64
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

SUPABASE_URL = "https://testref.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"


def _b64(n: int) -> str:
    largo = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(largo, "big")).rstrip(b"=").decode()


def _par_de_claves():
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    privada_pem = privada.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    publicos = privada.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "kid": "test-kid",
        "n": _b64(publicos.n),
        "e": _b64(publicos.e),
    }
    return privada_pem, jwk


@pytest.fixture(scope="session")
def claves_rsa():
    return _par_de_claves()


@pytest.fixture
def supabase_rs256(settings, claves_rsa):
    """Configura `settings` para validar RS256 contra un JWKS simulado."""
    privada_pem, jwk = claves_rsa
    settings.SUPABASE_URL = SUPABASE_URL
    settings.SUPABASE_JWT_SECRET = ""

    from shared.auth import supabase as modulo

    modulo.limpiar_cache_jwks()
    modulo._cache._refrescar = lambda: modulo._cache.__dict__.update(  # noqa: SLF001
        _claves={"test-kid": jwt.PyJWK(jwk).key},
        _expira_en=time.monotonic() + 3600,
    )
    yield privada_pem
    modulo.limpiar_cache_jwks()


@pytest.fixture
def supabase_hs256(settings):
    settings.SUPABASE_URL = ""
    settings.SUPABASE_JWT_SECRET = "secreto-de-prueba"
    from shared.auth import supabase as modulo

    modulo.limpiar_cache_jwks()
    return "secreto-de-prueba"


def construir_token(
    *,
    sub: str | uuid.UUID | None = None,
    correo: str = "persona@canchaya.test",
    nombre: str = "Persona Prueba",
    alg: str = "RS256",
    clave: str = "",
    kid: str | None = "test-kid",
    expira_en: int = 3600,
    audiencia: str = "authenticated",
    issuer: str | None = ISSUER,
    extra_claims: dict | None = None,
) -> str:
    ahora = int(time.time())
    payload = {
        "sub": str(sub or uuid.uuid4()),
        "aud": audiencia,
        "iat": ahora,
        "exp": ahora + expira_en,
        "email": correo,
        "user_metadata": {"email": correo, "full_name": nombre},
    }
    if issuer:
        payload["iss"] = issuer
    if extra_claims:
        payload.update(extra_claims)
    encabezado: dict = {"alg": alg, "typ": "JWT"}
    if kid:
        encabezado["kid"] = kid
    return jwt.encode(payload, clave, algorithm=alg, headers=encabezado)


def token_expirado(**kwargs) -> str:
    return construir_token(expira_en=-3600, **kwargs)


__all__ = ["SUPABASE_URL", "ISSUER", "construir_token", "token_expirado"]
