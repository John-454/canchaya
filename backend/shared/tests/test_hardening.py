"""T6.1 / T6.2 / T6.5 — Endurecimiento: throttling, CORS, esquema y errores."""

from __future__ import annotations

import uuid

import pytest
from django.core.cache import cache
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView

from shared.auth.authentication import SupabaseJWTAuthentication
from shared.openapi import SCHEMA
from shared.tests.tokens import construir_token

FIELD = "/api/v1/admin/field/"
SYNC = "/api/v1/auth/sync/"


@pytest.fixture(autouse=True)
def limpiar_throttle():
    """El throttle usa el cache local; se limpia entre tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestThrottle:
    def test_sync_se_limita_a_20_por_minuto(self, settings, supabase_rs256):
        settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth_sync"] = "3/min"
        api = APIClient()
        token = construir_token(clave=supabase_rs256, sub=uuid.uuid4())
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        codigos = [api.post(SYNC).status_code for _ in range(4)]
        assert codigos[:3] == [200, 200, 200]
        assert codigos[3] == 429

    def test_throttle_anonimo_por_ip(self):
        """AnonRateThrottle corta por IP aunque no haya token.

        En las rutas autenticadas el 401 se emite en `initial()` **antes** de
        `check_throttles()`, por eso se prueba con una vista pública con
        throttle de clase (mismo comportamiento por defecto de la API).
        """
        from rest_framework import throttling  # noqa: PLC0415

        class AnonLimite2(throttling.AnonRateThrottle):
            rate = "2/min"

        class VistaPublica(APIView):
            authentication_classes = []
            permission_classes = [AllowAny]
            throttle_classes = [AnonLimite2]

            def get(self, request):
                return Response({"ok": True})

        vista = VistaPublica.as_view()
        codigos = [vista(APIRequestFactory().get("/x/")).status_code for _ in range(3)]
        assert codigos[:2] == [200, 200]
        assert codigos[2] == 429

    def test_429_devuelve_el_formato_estandar(self, settings):
        settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth_sync"] = "1/min"
        api = APIClient()
        api.post(SYNC)
        resp = api.post(SYNC)
        assert resp.status_code == 429
        assert "code" in resp.data


@pytest.mark.django_db
class TestCabecerasYEsquema:
    def test_health_sin_throttle_no_falla(self):
        assert APIClient().get("/api/v1/health/").status_code == 200

    def test_esquema_openapi_disponible(self):
        resp = APIClient().get("/api/v1/schema/")
        assert resp.status_code == 200
        cuerpo = resp.json()
        assert cuerpo["openapi"].startswith("3.1")
        assert "/admin/bookings/{id_reserva}/approve/" in cuerpo["paths"]

    def test_esquema_cubre_todas_las_rutas_de_la_spec(self):
        rutas = set(SCHEMA["paths"])
        for obligatoria in [
            "/auth/sync/",
            "/auth/me/",
            "/admin/field/",
            "/admin/field/images/",
            "/admin/field/schedules/",
            "/admin/field/rates/",
            "/admin/field/rates/preview/",
            "/admin/bookings/",
            "/admin/finance/dashboard/",
            "/admin/finance/summary/",
        ]:
            assert obligatoria in rutas, obligatoria

    def test_rutas_protegidas_declaran_bearer(self):
        for ruta, operaciones in SCHEMA["paths"].items():
            if not ruta.startswith("/admin/"):
                continue
            for metodo, op in operaciones.items():
                assert op.get("security"), f"{metodo.upper()} {ruta} sin security"

    def test_esquema_publico_no_expone_secretos(self):
        import json

        texto = json.dumps(SCHEMA)
        assert "secret" not in texto.lower()
        assert "service_role" not in texto.lower()

    def test_cors_origen_permitido(self, settings):
        settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
        resp = APIClient().options(
            FIELD, HTTP_ORIGIN="http://localhost:5173", HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET"
        )
        assert resp["Access-Control-Allow-Origin"] == "http://localhost:5173"

    def test_cors_origen_no_permitido(self, settings):
        settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
        resp = APIClient().get(FIELD, HTTP_ORIGIN="https://malicioso.example")
        assert "Access-Control-Allow-Origin" not in resp

    def test_x_frame_options_deny(self):
        resp = APIClient().get("/api/v1/health/")
        assert resp["X-Frame-Options"] == "DENY"

    def test_nosniff(self):
        resp = APIClient().get("/api/v1/health/")
        assert resp["X-Content-Type-Options"] == "nosniff"


@pytest.mark.django_db
class TestContratoDeErrores:
    """Todos los errores del backend comparten la forma {code, detail}."""

    def test_401_tiene_codigo_y_reto(self):
        resp = APIClient().get(FIELD)
        assert resp.status_code == 401
        assert resp.data["code"] in {"not_authenticated", "token_invalido", "encabezado_invalido"}
        assert resp["WWW-Authenticate"]

    def test_403_rol(self, supabase_rs256, cliente):
        api = APIClient()
        api.credentials(
            HTTP_AUTHORIZATION=f"Bearer {construir_token(clave=supabase_rs256, sub=cliente.supabase_uid)}"
        )
        resp = api.get(FIELD)
        assert resp.status_code == 403
        assert resp.data["code"] == "rol_requerido"

    def test_404_reserva_ajena(self, supabase_rs256, admin_user, cancha):
        api = APIClient()
        api.credentials(
            HTTP_AUTHORIZATION=f"Bearer {construir_token(clave=supabase_rs256, sub=admin_user.supabase_uid)}"
        )
        resp = api.get("/api/v1/admin/bookings/999999/")
        assert resp.status_code == 404
        assert resp.data["code"] == "no_encontrado"
