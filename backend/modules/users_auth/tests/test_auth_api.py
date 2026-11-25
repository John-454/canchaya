"""T2.3 / T2.5 / T2.6 / T2.7 — Endpoints de auth, permisos y aprovisionamiento."""

from __future__ import annotations

import uuid

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient, APIRequestFactory
from shared.permissions import IsFieldAdmin
from shared.tests.tokens import construir_token

from modules.users_auth.models import Rol, Usuario

SYNC = "/api/v1/auth/sync/"
ME = "/api/v1/auth/me/"


def _auth(client: APIClient, token: str) -> APIClient:
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def api() -> APIClient:
    return APIClient()


# ---------------------------------------------------------------------------
# /auth/sync/
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestAuthSync:
    def test_crea_cliente_por_defecto(self, api, supabase_rs256):
        uid = uuid.uuid4()
        token = construir_token(clave=supabase_rs256, sub=uid, correo="nuevo@canchaya.test")
        resp = _auth(api, token).post(SYNC)
        assert resp.status_code == 200, resp.data
        assert resp.data["creado"] is True
        assert resp.data["rol"] == Rol.CLIENTE
        assert resp.data["requiere_telefono"] is True
        assert resp.data["telefono"] is None
        assert Usuario.objects.filter(supabase_uid=uid).count() == 1

    def test_es_idempotente(self, api, supabase_rs256):
        uid = uuid.uuid4()
        token = construir_token(clave=supabase_rs256, sub=uid, correo="idem@canchaya.test")
        _auth(api, token).post(SYNC)
        resp = _auth(api, token).post(SYNC)
        assert resp.data["creado"] is False
        assert Usuario.objects.count() == 1

    def test_actualiza_nombre_desde_supabase(self, api, supabase_rs256):
        uid = uuid.uuid4()
        _auth(api, construir_token(clave=supabase_rs256, sub=uid, nombre="Antes")).post(SYNC)
        resp = _auth(api, construir_token(clave=supabase_rs256, sub=uid, nombre="Después")).post(
            SYNC
        )
        assert resp.data["nombre"] == "Después"

    def test_no_sobrescribe_rol_existente(self, api, supabase_rs256):
        uid = uuid.uuid4()
        Usuario.objects.create(
            supabase_uid=uid, nombre="Admin", correo="adm@canchaya.test", rol=Rol.ADMINISTRADOR
        )
        resp = _auth(api, construir_token(clave=supabase_rs256, sub=uid)).post(SYNC)
        assert resp.data["rol"] == Rol.ADMINISTRADOR

    def test_vincula_perfil_aprovisionado_por_correo(self, api, supabase_rs256):
        uid = uuid.uuid4()
        Usuario.objects.create(
            supabase_uid=uuid.uuid4(),
            nombre="Propietario",
            correo="propietario@canchaya.test",
            rol=Rol.ADMINISTRADOR,
        )
        resp = _auth(
            api,
            construir_token(
                clave=supabase_rs256, sub=uid, correo="propietario@canchaya.test", nombre="X"
            ),
        ).post(SYNC)
        assert resp.status_code == 200
        assert resp.data["rol"] == Rol.ADMINISTRADOR
        assert resp.data["supabase_uid"] == str(uid)

    def test_sin_token(self, api):
        assert api.post(SYNC).status_code == 401

    def test_token_expirado(self, api, supabase_rs256):
        token = construir_token(clave=supabase_rs256, expira_en=-10)
        resp = _auth(api, token).post(SYNC)
        assert resp.status_code == 401
        assert resp.data["code"] == "token_expirado"

    def test_cuenta_desactivada(self, api, supabase_rs256):
        uid = uuid.uuid4()
        Usuario.objects.create(
            supabase_uid=uid, nombre="Off", correo="off2@canchaya.test", activo=False
        )
        resp = _auth(api, construir_token(clave=supabase_rs256, sub=uid)).post(SYNC)
        assert resp.status_code == 403
        assert resp.data["code"] == "cuenta_desactivada"


# ---------------------------------------------------------------------------
# /auth/me/
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestAuthMe:
    def test_get_perfil(self, api, supabase_rs256, cliente):
        token = construir_token(clave=supabase_rs256, sub=cliente.supabase_uid)
        resp = _auth(api, token).get(ME)
        assert resp.status_code == 200
        assert resp.data["correo"] == cliente.correo
        assert resp.data["requiere_telefono"] is False

    def test_requiere_autenticacion(self, api):
        assert api.get(ME).status_code == 401

    def test_patch_nombre_y_telefono(self, api, supabase_rs256, cliente):
        token = construir_token(clave=supabase_rs256, sub=cliente.supabase_uid)
        resp = _auth(api, token).patch(
            ME, {"nombre": "Cliente Renombrado", "telefono": "3001112233"}, format="json"
        )
        assert resp.status_code == 200, resp.data
        assert resp.data["nombre"] == "Cliente Renombrado"
        assert resp.data["telefono"] == "+573001112233"

    @pytest.mark.parametrize("telefono", ["12345", "abc", "6011234567", "30011122334"])
    def test_telefono_invalido(self, api, supabase_rs256, cliente, telefono):
        token = construir_token(clave=supabase_rs256, sub=cliente.supabase_uid)
        resp = _auth(api, token).patch(ME, {"telefono": telefono}, format="json")
        assert resp.status_code == 400
        assert resp.data["code"] == "telefono_invalido"

    def test_telefono_vacio_lo_limpia(self, api, supabase_rs256, cliente):
        token = construir_token(clave=supabase_rs256, sub=cliente.supabase_uid)
        resp = _auth(api, token).patch(ME, {"telefono": ""}, format="json")
        assert resp.status_code == 200
        assert resp.data["telefono"] is None
        assert resp.data["requiere_telefono"] is True

    @pytest.mark.parametrize("campo", ["rol", "activo", "supabase_uid", "correo"])
    def test_campos_protegidos(self, api, supabase_rs256, cliente, campo):
        token = construir_token(clave=supabase_rs256, sub=cliente.supabase_uid)
        valor = "administrador" if campo == "rol" else (True if campo == "activo" else "x@y.co")
        resp = _auth(api, token).patch(ME, {campo: valor}, format="json")
        assert resp.status_code == 400
        assert resp.data["code"] == "campo_no_permitido"

    def test_body_vacio(self, api, supabase_rs256, cliente):
        token = construir_token(clave=supabase_rs256, sub=cliente.supabase_uid)
        assert _auth(api, token).patch(ME, {}, format="json").status_code == 400


# ---------------------------------------------------------------------------
# IsFieldAdmin (aislamiento 1:1)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestIsFieldAdmin:
    factory = APIRequestFactory()

    def _request(self, usuario):
        request = self.factory.get("/x/")
        request.user = usuario
        return request

    def test_admin_con_cancha(self, admin_user, cancha):
        request = self._request(admin_user)
        assert IsFieldAdmin().has_permission(request, None) is True
        assert request.cancha.pk == cancha.pk

    def test_es_la_cancha_propia_y_no_otra(self, admin_user, cancha):
        otro = Usuario.objects.create(
            supabase_uid=uuid.uuid4(),
            nombre="Otro Admin",
            correo="otro@canchaya.test",
            rol=Rol.ADMINISTRADOR,
        )
        request = self._request(admin_user)
        IsFieldAdmin().has_permission(request, None)
        assert request.cancha.id_administrador_id == admin_user.pk
        assert request.cancha.id_administrador_id != otro.pk

    def test_admin_sin_cancha(self):
        from shared.exceptions import ADMIN_SIN_CANCHA, ForbiddenError

        admin = Usuario.objects.create(
            supabase_uid=uuid.uuid4(),
            nombre="Sin Cancha",
            correo="sincancha@canchaya.test",
            rol=Rol.ADMINISTRADOR,
        )
        with pytest.raises(ForbiddenError) as exc:
            IsFieldAdmin().has_permission(self._request(admin), None)
        assert exc.value.code == ADMIN_SIN_CANCHA

    def test_cliente_no_pasa(self, cliente):
        from shared.exceptions import ROL_REQUERIDO, ForbiddenError

        with pytest.raises(ForbiddenError) as exc:
            IsFieldAdmin().has_permission(self._request(cliente), None)
        assert exc.value.code == ROL_REQUERIDO

    def test_anonimo_no_pasa(self):
        from django.contrib.auth.models import AnonymousUser

        assert IsFieldAdmin().has_permission(self._request(AnonymousUser()), None) is False


# ---------------------------------------------------------------------------
# Aprovisionamiento (Opción A)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestAprovisionamientoAdmin:
    def test_crea_admin_nuevo(self):
        uid = uuid.uuid4()
        call_command(
            "aprovisionar_admin",
            "--correo=nuevo-admin@canchaya.test",
            f"--uid={uid}",
            "--nombre=Nueva Admin",
            "--telefono=3001234567",
            "--cancha=Cancha Nueva",
        )
        admin = Usuario.objects.get(correo="nuevo-admin@canchaya.test")
        assert admin.rol == Rol.ADMINISTRADOR
        assert admin.supabase_uid == uid
        assert admin.cancha.nombre == "Cancha Nueva"

    def test_promueve_cliente_existente(self, cliente):
        call_command(
            "aprovisionar_admin",
            f"--correo={cliente.correo}",
            f"--uid={uuid.uuid4()}",
        )
        cliente.refresh_from_db()
        assert cliente.rol == Rol.ADMINISTRADOR

    def test_vincula_seed_por_correo(self):
        seed = Usuario.objects.create(
            supabase_uid=uuid.uuid4(),
            nombre="Propietario Demo",
            correo="propietario@canchaya.test",
            rol=Rol.ADMINISTRADOR,
        )
        uid = uuid.uuid4()
        call_command("aprovisionar_admin", "--correo=propietario@canchaya.test", f"--uid={uid}")
        seed.refresh_from_db()
        assert seed.supabase_uid == uid

    def test_uid_duplicado_falla(self, admin_user):
        from django.core.management.base import CommandError

        with pytest.raises(CommandError):
            call_command(
                "aprovisionar_admin",
                "--correo=duplicado@canchaya.test",
                f"--uid={admin_user.supabase_uid}",
            )

    def test_sin_uid_ni_perfil_falla(self):
        from django.core.management.base import CommandError

        with pytest.raises(CommandError):
            call_command("aprovisionar_admin", "--correo=fantasma@canchaya.test")

    def test_telefono_invalido_falla(self):
        from django.core.management.base import CommandError

        with pytest.raises(CommandError):
            call_command(
                "aprovisionar_admin",
                "--correo=tel@canchaya.test",
                f"--uid={uuid.uuid4()}",
                "--telefono=123",
            )


# ---------------------------------------------------------------------------
# Servicio require_telefono (R1)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestRequiereTelefono:
    def test_cliente_sin_telefono(self):
        from shared.exceptions import TELEFONO_REQUERIDO, BusinessRuleViolation

        from modules.users_auth import services

        usuario = Usuario.objects.create(
            supabase_uid=uuid.uuid4(), nombre="Google", correo="google@canchaya.test"
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            services.require_telefono(usuario)
        assert exc.value.code == TELEFONO_REQUERIDO

    def test_con_telefono_pasa(self, cliente):
        from modules.users_auth import services

        assert services.require_telefono(cliente) == cliente.telefono
