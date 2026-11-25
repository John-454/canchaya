"""T3.4 – T3.8 — API del panel: Mi cancha, fotos, horarios, tarifas y preview."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from shared.tests.tokens import construir_token

from modules.fields.models import Cancha, HorarioOperacion, ImagenCancha, Tarifa
from modules.users_auth.models import Rol, Usuario

FIELD = "/api/v1/admin/field/"
IMAGES = f"{FIELD}images/"
SCHEDULES = f"{FIELD}schedules/"
RATES = f"{FIELD}rates/"
PREVIEW = f"{FIELD}rates/preview/"
QUOTE = f"{FIELD}rates/quote/"


@pytest.fixture
def admin_api(admin_user, cancha, supabase_rs256) -> APIClient:
    cliente = APIClient()
    cliente.credentials(
        HTTP_AUTHORIZATION=f"Bearer {construir_token(clave=supabase_rs256, sub=admin_user.supabase_uid)}"
    )
    return cliente


def _h(t: str) -> dt.time:
    return dt.time.fromisoformat(t)


# ---------------------------------------------------------------------------
# Mi cancha
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestMiCancha:
    def test_get_devuelve_su_cancha(self, admin_api, cancha):
        resp = admin_api.get(FIELD)
        assert resp.status_code == 200
        assert resp.data["id_cancha"] == cancha.pk
        assert resp.data["nombre"] == cancha.nombre

    def test_patch_actualiza_campos(self, admin_api, cancha):
        resp = admin_api.patch(
            FIELD,
            {"nombre": "Cancha Sur", "precio_base": "75000.00", "estado": False},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        cancha.refresh_from_db()
        assert cancha.nombre == "Cancha Sur"
        assert cancha.precio_base == Decimal("75000.00")
        assert cancha.estado is False

    def test_nombre_vacio_rechazado(self, admin_api, cancha):
        assert admin_api.patch(FIELD, {"nombre": "  "}, format="json").status_code == 400

    def test_precio_negativo_rechazado(self, admin_api, cancha):
        assert admin_api.patch(FIELD, {"precio_base": "-1"}, format="json").status_code == 400


# ---------------------------------------------------------------------------
# Aislamiento 1:1 y admin sin cancha
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestAislamiento:
    def test_admin_sin_cancha_403(self, supabase_rs256):
        admin = Usuario.objects.create(
            supabase_uid=uuid.uuid4(),
            nombre="Admin Vacío",
            correo="vacio@canchaya.test",
            rol=Rol.ADMINISTRADOR,
        )
        api = APIClient()
        api.credentials(
            HTTP_AUTHORIZATION=f"Bearer {construir_token(clave=supabase_rs256, sub=admin.supabase_uid)}"
        )
        resp = api.get(FIELD)
        assert resp.status_code == 403
        assert resp.data["code"] == "admin_sin_cancha"

    def test_cliente_403(self, supabase_rs256, cliente):
        api = APIClient()
        api.credentials(
            HTTP_AUTHORIZATION=f"Bearer {construir_token(clave=supabase_rs256, sub=cliente.supabase_uid)}"
        )
        resp = api.get(FIELD)
        assert resp.status_code == 403
        assert resp.data["code"] == "rol_requerido"

    def test_sin_token_401(self):
        resp = APIClient().get(FIELD)
        assert resp.status_code == 401
        assert resp["WWW-Authenticate"]

    def test_admin_b_no_ve_ni_toca_la_cancha_de_a(self, admin_api, cancha, supabase_rs256):
        # Admin B con su propia cancha e imágenes.
        admin_b = Usuario.objects.create(
            supabase_uid=uuid.uuid4(),
            nombre="Admin B",
            correo="adminb@canchaya.test",
            rol=Rol.ADMINISTRADOR,
        )
        cancha_b = Cancha.objects.create(
            id_administrador=admin_b,
            nombre="Cancha B",
            direccion="Otra",
            precio_base=Decimal("50000"),
        )
        imagen_b = ImagenCancha.objects.create(
            id_cancha=cancha_b, url_imagen="https://x.test/b.jpg", imagen_principal=True
        )
        horario_b = HorarioOperacion.objects.create(
            id_cancha=cancha_b, dia_semana=1, hora_apertura=_h("08:00"), hora_cierre=_h("10:00")
        )
        tarifa_b = Tarifa.objects.create(
            id_cancha=cancha_b,
            dia_semana=1,
            hora_inicio=_h("08:00"),
            hora_fin=_h("10:00"),
            precio_hora=Decimal("10"),
        )

        # Admin A (su token) solo ve SU cancha
        assert admin_api.get(FIELD).data["id_cancha"] == cancha.pk
        assert admin_api.get(IMAGES).data == []
        assert admin_api.get(SCHEDULES).data == []
        assert admin_api.get(RATES).data == []

        # IDs de la cancha de B -> 404 (no filtra existencia)
        assert (
            admin_api.patch(
                f"{IMAGES}{imagen_b.pk}/", {"imagen_principal": True}, format="json"
            ).status_code
            == 404
        )
        assert admin_api.delete(f"{IMAGES}{imagen_b.pk}/").status_code == 404
        assert admin_api.delete(f"{SCHEDULES}{horario_b.pk}/").status_code == 404
        assert admin_api.delete(f"{RATES}{tarifa_b.pk}/").status_code == 404

        # Y nada se borró
        assert ImagenCancha.objects.filter(pk=imagen_b.pk).exists()
        assert HorarioOperacion.objects.filter(pk=horario_b.pk).exists()
        assert Tarifa.objects.filter(pk=tarifa_b.pk).exists()


# ---------------------------------------------------------------------------
# Fotografías
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestImagenes:
    def test_primera_imagen_es_principal_automaticamente(self, admin_api, cancha):
        resp = admin_api.post(IMAGES, {"url_imagen": "https://x.test/1.jpg"}, format="json")
        assert resp.status_code == 201
        assert resp.data["imagen_principal"] is True
        assert cancha.imagenes.count() == 1

    def test_marcar_principal_desmarca_la_anterior(self, admin_api, cancha):
        admin_api.post(IMAGES, {"url_imagen": "https://x.test/1.jpg"}, format="json")
        segunda = admin_api.post(IMAGES, {"url_imagen": "https://x.test/2.jpg"}, format="json")
        assert segunda.data["imagen_principal"] is False

        resp = admin_api.patch(
            f"{IMAGES}{segunda.data['id_imagen']}/", {"imagen_principal": True}, format="json"
        )
        assert resp.status_code == 200
        assert cancha.imagenes.filter(imagen_principal=True).count() == 1
        assert cancha.imagenes.get(imagen_principal=True).pk == segunda.data["id_imagen"]

    def test_url_invalida_rechazada(self, admin_api):
        assert (
            admin_api.post(IMAGES, {"url_imagen": "ftp://nope"}, format="json").status_code == 400
        )

    def test_borrar_principal_promueve_la_mas_antigua(self, admin_api, cancha):
        primera = admin_api.post(IMAGES, {"url_imagen": "https://x.test/1.jpg"}, format="json")
        segunda = admin_api.post(IMAGES, {"url_imagen": "https://x.test/2.jpg"}, format="json")
        assert admin_api.delete(f"{IMAGES}{primera.data['id_imagen']}/").status_code == 204
        restante = cancha.imagenes.get(pk=segunda.data["id_imagen"])
        assert restante.imagen_principal is True

    def test_editar_descripcion(self, admin_api, cancha):
        creada = admin_api.post(IMAGES, {"url_imagen": "https://x.test/1.jpg"}, format="json")
        resp = admin_api.patch(
            f"{IMAGES}{creada.data['id_imagen']}/", {"descripcion": "Frente"}, format="json"
        )
        assert resp.data["descripcion"] == "Frente"
        assert cancha.imagenes.get().imagen_principal is True


# ---------------------------------------------------------------------------
# Horarios
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestHorarios:
    def test_crear_y_listar(self, admin_api):
        resp = admin_api.post(
            SCHEDULES,
            {"dia_semana": 1, "hora_apertura": "08:00", "hora_cierre": "12:00"},
            format="json",
        )
        assert resp.status_code == 201, resp.data
        assert len(admin_api.get(SCHEDULES).data) == 1

    def test_solape_409(self, admin_api, horario):
        horario(dia=1, abre="08:00", cierra="12:00")
        resp = admin_api.post(
            SCHEDULES,
            {"dia_semana": 1, "hora_apertura": "11:00", "hora_cierre": "13:00"},
            format="json",
        )
        assert resp.status_code == 409
        assert resp.data["code"] == "horario_solapado"

    def test_franjas_contiguas_permitidas(self, admin_api, horario):
        horario(dia=1, abre="08:00", cierra="12:00")
        resp = admin_api.post(
            SCHEDULES,
            {"dia_semana": 1, "hora_apertura": "12:00", "hora_cierre": "14:00"},
            format="json",
        )
        assert resp.status_code == 201

    def test_hora_no_en_punto_400(self, admin_api):
        resp = admin_api.post(
            SCHEDULES,
            {"dia_semana": 1, "hora_apertura": "08:30", "hora_cierre": "12:00"},
            format="json",
        )
        assert resp.status_code == 400

    def test_cierre_antes_de_apertura_400(self, admin_api):
        resp = admin_api.post(
            SCHEDULES,
            {"dia_semana": 1, "hora_apertura": "13:00", "hora_cierre": "12:00"},
            format="json",
        )
        assert resp.status_code == 400

    def test_dia_invalido_400(self, admin_api):
        resp = admin_api.post(
            SCHEDULES,
            {"dia_semana": 9, "hora_apertura": "08:00", "hora_cierre": "12:00"},
            format="json",
        )
        assert resp.status_code == 400

    def test_put_actualiza_y_delete(self, admin_api, horario):
        h = horario(dia=2, abre="08:00", cierra="12:00")
        resp = admin_api.put(
            f"{SCHEDULES}{h.pk}/",
            {"dia_semana": 2, "hora_apertura": "09:00", "hora_cierre": "13:00"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["hora_apertura"] == "09:00:00"
        assert admin_api.delete(f"{SCHEDULES}{h.pk}/").status_code == 204

    def test_put_que_genera_solape_409(self, admin_api, horario):
        a = horario(dia=1, abre="08:00", cierra="10:00")
        horario(dia=1, abre="10:00", cierra="12:00")
        resp = admin_api.put(
            f"{SCHEDULES}{a.pk}/",
            {"dia_semana": 1, "hora_apertura": "08:00", "hora_cierre": "11:00"},
            format="json",
        )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Tarifas
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestTarifas:
    def test_crear_semanal(self, admin_api):
        resp = admin_api.post(
            RATES,
            {"dia_semana": 3, "hora_inicio": "08:00", "hora_fin": "10:00", "precio_hora": "80000"},
            format="json",
        )
        assert resp.status_code == 201, resp.data
        assert resp.data["origen"] == "semanal"

    def test_crear_especial(self, admin_api):
        resp = admin_api.post(
            RATES,
            {
                "fecha_especial": "2026-12-24",
                "hora_inicio": "08:00",
                "hora_fin": "12:00",
                "precio_hora": "95000",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["origen"] == "especial"

    def test_debe_indicar_exactamente_un_tipo(self, admin_api):
        sin_tipo = admin_api.post(
            RATES, {"hora_inicio": "08:00", "hora_fin": "10:00", "precio_hora": "1"}, format="json"
        )
        ambos = admin_api.post(
            RATES,
            {
                "dia_semana": 1,
                "fecha_especial": "2026-12-24",
                "hora_inicio": "08:00",
                "hora_fin": "10:00",
                "precio_hora": "1",
            },
            format="json",
        )
        assert sin_tipo.status_code == 400
        assert ambos.status_code == 400

    def test_solape_semanal_409(self, admin_api, tarifa):
        tarifa(dia=1, inicio="08:00", fin="10:00")
        resp = admin_api.post(
            RATES,
            {"dia_semana": 1, "hora_inicio": "09:00", "hora_fin": "11:00", "precio_hora": "1"},
            format="json",
        )
        assert resp.status_code == 409
        assert resp.data["code"] == "tarifa_solapada"

    def test_especial_y_semanal_no_chocan(self, admin_api, tarifa):
        tarifa(dia=4, inicio="08:00", fin="12:00")
        resp = admin_api.post(
            RATES,
            {
                "fecha_especial": "2026-12-24",
                "hora_inicio": "08:00",
                "hora_fin": "12:00",
                "precio_hora": "95000",
            },
            format="json",
        )
        assert resp.status_code == 201

    def test_precio_cero_400(self, admin_api):
        resp = admin_api.post(
            RATES,
            {"dia_semana": 1, "hora_inicio": "08:00", "hora_fin": "10:00", "precio_hora": "0"},
            format="json",
        )
        assert resp.status_code == 400

    def test_patch_y_delete(self, admin_api, tarifa):
        t = tarifa(dia=1, inicio="08:00", fin="10:00")
        resp = admin_api.patch(f"{RATES}{t.pk}/", {"precio_hora": "99000"}, format="json")
        assert resp.status_code == 200
        assert Decimal(resp.data["precio_hora"]) == Decimal("99000.00")
        assert admin_api.delete(f"{RATES}{t.pk}/").status_code == 204


# ---------------------------------------------------------------------------
# Vista previa de precios
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestPreview:
    def test_preview_con_prioridades(self, admin_api, cancha, horario, tarifa):
        # martes 2026-12-01
        horario(dia=2, abre="08:00", cierra="12:00")
        tarifa(dia=2, inicio="08:00", fin="10:00", precio="70000")
        tarifa(fecha=dt.date(2026, 12, 1), inicio="09:00", fin="11:00", precio="99000")

        resp = admin_api.get(PREVIEW, {"fecha": "2026-12-01"})
        assert resp.status_code == 200
        bloques = {b["hora_inicio"]: b for b in resp.data["bloques"]}
        assert len(bloques) == 4
        assert bloques["08:00"]["origen"] == "semanal"
        assert bloques["09:00"]["origen"] == "especial"
        assert bloques["10:00"]["origen"] == "especial"
        assert bloques["11:00"]["origen"] == "base"
        assert bloques["11:00"]["precio"] == "60000.00"

    def test_preview_sin_fecha_400(self, admin_api):
        assert admin_api.get(PREVIEW).status_code == 400

    def test_preview_fecha_invalida_400(self, admin_api):
        assert admin_api.get(PREVIEW, {"fecha": "2026-13-45"}).status_code == 400

    def test_preview_dia_sin_horario(self, admin_api):
        resp = admin_api.get(PREVIEW, {"fecha": "2026-12-01"})
        assert resp.status_code == 200
        assert resp.data["bloques"] == []


# ---------------------------------------------------------------------------
# Cotización de un rango (apoyo a bookings)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestQuote:
    def test_cotiza_rango(self, admin_api, horario):
        horario(dia=2, abre="08:00", cierra="12:00")
        resp = admin_api.get(QUOTE, {"fecha": "2026-12-01", "inicio": "08:00", "fin": "10:00"})
        assert resp.status_code == 200
        assert resp.data["precio_total"] == "120000.00"

    def test_rango_en_hueco_400(self, admin_api, horario):
        horario(dia=2, abre="08:00", cierra="12:00")
        horario(dia=2, abre="13:00", cierra="22:00")
        resp = admin_api.get(QUOTE, {"fecha": "2026-12-01", "inicio": "11:00", "fin": "14:00"})
        assert resp.status_code == 400
        assert resp.data["code"] == "fuera_de_horario"

    def test_parametros_invalidos_400(self, admin_api):
        assert (
            admin_api.get(QUOTE, {"fecha": "x", "inicio": "08:00", "fin": "09:00"}).status_code
            == 400
        )
