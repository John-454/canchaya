"""T2.1 / T2.2 — Validación de JWT de Supabase y autenticación DRF."""

from __future__ import annotations

import uuid

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from modules.users_auth.models import Rol, Usuario
from rest_framework.test import APIRequestFactory

from shared.auth import supabase
from shared.auth.authentication import SupabaseJWTAuthentication
from shared.tests.tokens import construir_token, token_expirado


class TestVerificacionRS256:
    def test_token_valido_rs256(self, supabase_rs256):
        token = construir_token(clave=supabase_rs256, sub=uuid.uuid4(), correo="a@b.co")
        claims = supabase.verificar_token(token)
        assert claims.correo == "a@b.co"
        assert claims.nombre == "Persona Prueba"

    def test_token_expirado(self, supabase_rs256):
        token = token_expirado(clave=supabase_rs256)
        with pytest.raises(supabase.TokenExpirado) as exc:
            supabase.verificar_token(token)
        assert exc.value.code == "token_expirado"

    def test_firma_invalida(self, supabase_rs256):
        # Firma con otra clave RSA pero el mismo `kid` del JWKS simulado.
        otra = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        otra_pem = otra.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        with pytest.raises(supabase.TokenInvalido):
            supabase.verificar_token(construir_token(clave=otra_pem))

    def test_audiencia_incorrecta(self, supabase_rs256):
        token = construir_token(clave=supabase_rs256, audiencia="otra")
        with pytest.raises(supabase.TokenInvalido):
            supabase.verificar_token(token)

    def test_emisor_incorrecto(self, supabase_rs256):
        token = construir_token(clave=supabase_rs256, issuer="https://otro.co/auth/v1")
        with pytest.raises(supabase.TokenInvalido):
            supabase.verificar_token(token)

    def test_kid_desconocido(self, supabase_rs256):
        token = construir_token(clave=supabase_rs256, kid="otro-kid")
        with pytest.raises(supabase.TokenInvalido):
            supabase.verificar_token(token)

    def test_sin_url_configurada(self, settings, claves_rsa):
        settings.SUPABASE_URL = ""
        settings.SUPABASE_JWT_SECRET = ""
        with pytest.raises(supabase.ConfiguracionAusente):
            supabase.verificar_token(construir_token(clave=claves_rsa[0]))


class TestVerificacionHS256:
    def test_token_valido_hs256(self, supabase_hs256):
        token = construir_token(
            alg="HS256", clave=supabase_hs256, kid=None, correo="hs@canchaya.test"
        )
        assert supabase.verificar_token(token).correo == "hs@canchaya.test"

    def test_secreto_incorrecto(self, supabase_hs256):
        token = construir_token(alg="HS256", clave="otro-secreto", kid=None)
        with pytest.raises(supabase.TokenInvalido):
            supabase.verificar_token(token)


class TestFormato:
    def test_token_vacio(self):
        with pytest.raises(supabase.TokenInvalido):
            supabase.verificar_token("")

    def test_token_basura(self):
        with pytest.raises(supabase.TokenInvalido):
            supabase.verificar_token("no-es-un-jwt")

    def test_algoritmo_no_soportado(self, supabase_hs256):
        import jwt as pyjwt

        token = pyjwt.encode({"sub": "x", "aud": "authenticated"}, "k", algorithm="HS384")
        with pytest.raises(supabase.TokenInvalido):
            supabase.verificar_token(token)


@pytest.mark.django_db
class TestAutenticacionDRF:
    factory = APIRequestFactory()

    def _req(self, token: str | None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.factory.get("/api/v1/auth/me/", **headers)

    def test_sin_encabezado_devuelve_none(self, supabase_rs256):
        assert SupabaseJWTAuthentication().authenticate(self._req(None)) is None

    def test_encabezado_mal_formado(self, supabase_rs256):
        from rest_framework.exceptions import AuthenticationFailed

        req = self.factory.get("/x/", HTTP_AUTHORIZATION="Token abc")
        with pytest.raises(AuthenticationFailed):
            SupabaseJWTAuthentication().authenticate(req)

    def test_usuario_existente(self, supabase_rs256, cliente):
        token = construir_token(clave=supabase_rs256, sub=cliente.supabase_uid)
        usuario, _ = SupabaseJWTAuthentication().authenticate(self._req(token))
        assert usuario.pk == cliente.pk

    def test_perfil_no_sincronizado(self, supabase_rs256):
        from rest_framework.exceptions import AuthenticationFailed

        token = construir_token(clave=supabase_rs256, sub=uuid.uuid4())
        with pytest.raises(AuthenticationFailed) as exc:
            SupabaseJWTAuthentication().authenticate(self._req(token))
        assert exc.value.detail.code == "perfil_no_sincronizado"

    def test_cuenta_desactivada(self, supabase_rs256):
        from rest_framework.exceptions import PermissionDenied

        uid = uuid.uuid4()
        Usuario.objects.create(
            supabase_uid=uid, nombre="Off", correo="off@canchaya.test", activo=False
        )
        token = construir_token(clave=supabase_rs256, sub=uid)
        with pytest.raises(PermissionDenied) as exc:
            SupabaseJWTAuthentication().authenticate(self._req(token))
        assert exc.value.detail.code == "cuenta_desactivada"

    def test_un_perfil_por_uid_y_por_correo_coincide(self, supabase_rs256):
        """Si el perfil existe por correo pero con otro uid, se vincula al token."""
        uid = uuid.uuid4()
        Usuario.objects.create(
            supabase_uid=uuid.uuid4(),
            nombre="Admin",
            correo="admin@canchaya.test",
            rol=Rol.ADMINISTRADOR,
        )
        token = construir_token(
            clave=supabase_rs256, sub=uid, correo="admin@canchaya.test", nombre="Nombre Supabase"
        )
        usuario, _ = SupabaseJWTAuthentication().authenticate(self._req(token))
        assert usuario.rol == Rol.ADMINISTRADOR
        assert usuario.supabase_uid == uid
        # El nombre del admin no se sobrescribe con el de Supabase.
        assert usuario.nombre == "Admin"
