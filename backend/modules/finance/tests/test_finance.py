"""T4.9 – T4.11 — Dashboard y contabilidad; T4.4 – T4.7 API de reservas."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from shared.exceptions import ValidationError
from shared.tests.tokens import construir_token

from modules.bookings.models import EstadoPago, EstadoReserva
from modules.fields.models import HorarioOperacion
from modules.finance import selectors
from modules.users_auth.models import Rol, Usuario

HOY = timezone.localdate()
AYER = HOY - dt.timedelta(days=1)
MANANA = HOY + dt.timedelta(days=1)

BOOKINGS = "/api/v1/admin/bookings/"
DASHBOARD = "/api/v1/admin/finance/dashboard/"
SUMMARY = "/api/v1/admin/finance/summary/"


def _h(t: str) -> dt.time:
    return dt.time.fromisoformat(t)


@pytest.fixture
def cancha_full(cancha):
    for dia in range(1, 8):
        for abre, cierra in (("08:00", "12:00"), ("13:00", "22:00")):
            HorarioOperacion.objects.create(
                id_cancha=cancha,
                dia_semana=dia,
                hora_apertura=_h(abre),
                hora_cierre=_h(cierra),
            )
    return cancha


@pytest.fixture
def api(admin_user, supabase_rs256) -> APIClient:
    cliente = APIClient()
    cliente.credentials(
        HTTP_AUTHORIZATION=f"Bearer {construir_token(clave=supabase_rs256, sub=admin_user.supabase_uid)}"
    )
    return cliente


# ---------------------------------------------------------------------------
# Agregaciones (§3.4)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestAgregaciones:
    def _set(self, reserva, **kw):
        return reserva(
            fecha=kw.pop("fecha", HOY),
            inicio=kw.pop("inicio", "08:00"),
            fin=kw.pop("fin", "09:00"),
            **kw,
        )

    def test_matriz_estado_x_pago(self, cancha_full, reserva):
        pagado = dict(pago=EstadoPago.PAGADO, fecha_pago=timezone.now())
        self._set(
            reserva,
            fecha=AYER,
            inicio="08:00",
            fin="09:00",
            estado=EstadoReserva.CONFIRMADA,
            **pagado,
            precio="60000",
        )
        self._set(
            reserva,
            fecha=AYER,
            inicio="09:00",
            fin="10:00",
            estado=EstadoReserva.FINALIZADA,
            **pagado,
            precio="100000",
        )
        self._set(
            reserva,
            fecha=AYER,
            inicio="10:00",
            fin="11:00",
            estado=EstadoReserva.CONFIRMADA,
            precio="70000",
        )
        self._set(
            reserva,
            fecha=AYER,
            inicio="11:00",
            fin="12:00",
            estado=EstadoReserva.FINALIZADA,
            precio="30000",
        )
        # Estas NO cuentan
        self._set(
            reserva,
            fecha=AYER,
            inicio="13:00",
            fin="14:00",
            estado=EstadoReserva.PENDIENTE,
            **pagado,
            precio="999999",
        )
        self._set(
            reserva,
            fecha=AYER,
            inicio="14:00",
            fin="15:00",
            estado=EstadoReserva.CANCELADA,
            **pagado,
            precio="888888",
        )
        self._set(
            reserva,
            fecha=AYER,
            inicio="15:00",
            fin="16:00",
            estado=EstadoReserva.CANCELADA,
            precio="777777",
        )

        assert selectors.ingresos_recibidos(cancha_full) == Decimal("160000.00")
        assert selectors.dinero_pendiente(cancha_full) == Decimal("100000.00")

    def test_sin_reservas_devuelve_cero(self, cancha_full):
        assert selectors.ingresos_recibidos(cancha_full) == Decimal("0.00")
        assert selectors.dinero_pendiente(cancha_full) == Decimal("0.00")

    def test_filtra_por_rango(self, cancha_full, reserva):
        pagado = dict(pago=EstadoPago.PAGADO, fecha_pago=timezone.now())
        self._set(reserva, fecha=AYER, estado=EstadoReserva.CONFIRMADA, **pagado, precio="10000")
        self._set(reserva, fecha=HOY, estado=EstadoReserva.CONFIRMADA, **pagado, precio="20000")

        assert selectors.ingresos_recibidos(cancha_full, HOY, HOY) == Decimal("20000.00")
        assert selectors.ingresos_recibidos(cancha_full, AYER, HOY) == Decimal("30000.00")

    def test_solo_su_cancha(self, cancha_full, reserva, admin_user):
        from modules.fields.models import Cancha

        otro = Usuario.objects.create(
            supabase_uid=__import__("uuid").uuid4(),
            nombre="Otro",
            correo="otro2@canchaya.test",
            rol=Rol.ADMINISTRADOR,
        )
        cancha_b = Cancha.objects.create(
            id_administrador=otro, nombre="B", direccion="x", precio_base=Decimal("1")
        )
        self._set(
            reserva,
            fecha=HOY,
            estado=EstadoReserva.CONFIRMADA,
            pago=EstadoPago.PAGADO,
            fecha_pago=timezone.now(),
            precio="50000",
        )
        from modules.bookings.models import Reserva

        Reserva.objects.create(
            codigo_reserva="CY-240801-OTRA",
            id_cancha=cancha_b,
            id_cliente=admin_user,
            nombre_cliente="x",
            correo_cliente="x@x.co",
            telefono_cliente="3000000000",
            fecha_reserva=HOY,
            hora_inicio=_h("08:00"),
            hora_fin=_h("09:00"),
            precio_total=Decimal("999999"),
            estado_reserva=EstadoReserva.CONFIRMADA,
            estado_pago=EstadoPago.PAGADO,
            fecha_pago=timezone.now(),
        )
        assert selectors.ingresos_recibidos(cancha_full) == Decimal("50000.00")


# ---------------------------------------------------------------------------
# Rangos
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestRangos:
    def test_day(self):
        r = selectors.resolver_rango("day", None, None)
        assert r.inicio == r.fin == HOY

    def test_week_lunes_a_domingo(self):
        r = selectors.resolver_rango("week", None, None)
        assert r.inicio.isoweekday() == 1
        assert (r.fin - r.inicio).days == 6

    def test_month(self):
        r = selectors.resolver_rango("month", None, None)
        assert r.inicio.day == 1
        assert (r.fin + dt.timedelta(days=1)).day == 1

    def test_custom_exige_fechas(self):
        with pytest.raises(ValidationError):
            selectors.resolver_rango("custom", None, None)

    def test_custom_invertido(self):
        with pytest.raises(ValidationError):
            selectors.resolver_rango("custom", "2026-12-10", "2026-12-01")

    def test_period_invalido(self):
        with pytest.raises(ValidationError):
            selectors.resolver_rango("year", None, None)


# ---------------------------------------------------------------------------
# API de reservas
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestApiReservas:
    def test_listado_paginado(self, api, cancha_full, reserva):
        for i in range(3):
            reserva(fecha=MANANA, inicio=f"{8 + i:02d}:00", fin=f"{9 + i:02d}:00")
        resp = api.get(BOOKINGS)
        assert resp.status_code == 200
        assert resp.data["count"] == 3
        assert len(resp.data["results"]) == 3

    def test_filtro_por_estado(self, api, cancha_full, reserva):
        reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        reserva(fecha=MANANA, inicio="10:00", fin="11:00", estado=EstadoReserva.CONFIRMADA)
        resp = api.get(BOOKINGS, {"estado_reserva": EstadoReserva.CONFIRMADA})
        assert resp.data["count"] == 1

    def test_filtro_por_codigo(self, api, cancha_full, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00", codigo="CY-999999-BUSC")
        resp = api.get(BOOKINGS, {"codigo_reserva": "BUSC"})
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["id_reserva"] == r.pk

    def test_filtro_estado_invalido_400(self, api, cancha_full):
        assert api.get(BOOKINGS, {"estado_reserva": "Talvez"}).status_code == 400

    def test_detalle(self, api, cancha_full, reserva, cliente):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        resp = api.get(f"{BOOKINGS}{r.pk}/")
        assert resp.status_code == 200
        assert resp.data["cliente"]["telefono"] == cliente.telefono

    def test_detalle_ajeno_404(self, api, cancha_full, reserva, admin_user):
        from decimal import Decimal

        from modules.bookings.models import Reserva
        from modules.fields.models import Cancha

        otro = Usuario.objects.create(
            supabase_uid=__import__("uuid").uuid4(),
            nombre="Otro",
            correo="otro3@canchaya.test",
            rol=Rol.ADMINISTRADOR,
        )
        cancha_b = Cancha.objects.create(
            id_administrador=otro, nombre="B", direccion="x", precio_base=Decimal("1")
        )
        ajena = Reserva.objects.create(
            codigo_reserva="CY-240801-AJEN",
            id_cancha=cancha_b,
            id_cliente=admin_user,
            nombre_cliente="x",
            correo_cliente="x@x.co",
            telefono_cliente="3000000000",
            fecha_reserva=MANANA,
            hora_inicio=_h("08:00"),
            hora_fin=_h("09:00"),
            precio_total=Decimal("1"),
            estado_reserva=EstadoReserva.PENDIENTE,
            estado_pago=EstadoPago.PENDIENTE,
        )
        assert api.get(f"{BOOKINGS}{ajena.pk}/").status_code == 404

    def test_aprobar(self, api, cancha_full, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        resp = api.post(f"{BOOKINGS}{r.pk}/approve/")
        assert resp.status_code == 200
        assert resp.data["estado_reserva"] == EstadoReserva.CONFIRMADA

    def test_aprobar_dos_veces_409(self, api, cancha_full, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        api.post(f"{BOOKINGS}{r.pk}/approve/")
        resp = api.post(f"{BOOKINGS}{r.pk}/approve/")
        assert resp.status_code == 409
        assert resp.data["code"] == "estado_invalido"

    def test_cancelar(self, api, cancha_full, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        resp = api.post(f"{BOOKINGS}{r.pk}/cancel/", {"motivo": "clima"}, format="json")
        assert resp.status_code == 200
        assert resp.data["estado_reserva"] == EstadoReserva.CANCELADA
        assert "clima" in resp.data["observaciones"]

    def test_marcar_pagado(self, api, cancha_full, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        resp = api.post(f"{BOOKINGS}{r.pk}/mark-paid/")
        assert resp.status_code == 200
        assert resp.data["estado_pago"] == EstadoPago.PAGADO
        assert resp.data["fecha_pago"] is not None

    def test_no_puede_aprobar_de_otro_admin(self, api, cancha_full, reserva, admin_user):
        from decimal import Decimal

        from modules.bookings.models import Reserva
        from modules.fields.models import Cancha

        otro = Usuario.objects.create(
            supabase_uid=__import__("uuid").uuid4(),
            nombre="Otro",
            correo="otro4@canchaya.test",
            rol=Rol.ADMINISTRADOR,
        )
        cancha_b = Cancha.objects.create(
            id_administrador=otro, nombre="B", direccion="x", precio_base=Decimal("1")
        )
        ajena = Reserva.objects.create(
            codigo_reserva="CY-240801-AJEN",
            id_cancha=cancha_b,
            id_cliente=admin_user,
            nombre_cliente="x",
            correo_cliente="x@x.co",
            telefono_cliente="3000000000",
            fecha_reserva=MANANA,
            hora_inicio=_h("08:00"),
            hora_fin=_h("09:00"),
            precio_total=Decimal("1"),
            estado_reserva=EstadoReserva.PENDIENTE,
            estado_pago=EstadoPago.PENDIENTE,
        )
        assert api.post(f"{BOOKINGS}{ajena.pk}/approve/").status_code == 404
        assert api.post(f"{BOOKINGS}{ajena.pk}/mark-paid/").status_code == 404


# ---------------------------------------------------------------------------
# Dashboard y summary
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestDashboard:
    def test_estructura(self, api, cancha_full):
        resp = api.get(DASHBOARD)
        assert resp.status_code == 200
        for clave in (
            "kpis",
            "serie_actividad",
            "serie_ingresos",
            "solicitudes_por_aprobar",
            "proximos_partidos",
        ):
            assert clave in resp.data
        assert resp.data["kpis"]["ingresos_recibidos"] == "0.00"
        assert len(resp.data["serie_actividad"]) == 30

    def test_kpis_reservas_de_hoy(self, api, cancha_full, reserva):
        reserva(fecha=HOY, inicio="08:00", fin="09:00")
        reserva(fecha=HOY, inicio="10:00", fin="11:00", estado=EstadoReserva.CONFIRMADA)
        reserva(fecha=HOY, inicio="13:00", fin="14:00", estado=EstadoReserva.CANCELADA)
        kpis = api.get(DASHBOARD).data["kpis"]

        # La reserva confirmada de hoy puede haber vencido ya (-> Finalizada),
        # así que solo se afirman los contadores estables.
        assert kpis["reservas_hoy"] == 3
        assert kpis["pendientes_hoy"] == 1
        assert kpis["canceladas_hoy"] == 1
        assert kpis["confirmadas_hoy"] in (0, 1)

    def test_reserva_confirmada_futura_cuenta_como_confirmada(self, api, cancha_full, reserva):
        reserva(fecha=MANANA, inicio="08:00", fin="09:00", estado=EstadoReserva.CONFIRMADA)
        data = api.get(DASHBOARD).data
        assert len(data["proximos_partidos"]) == 1

    def test_solicitudes_y_proximos(self, api, cancha_full, reserva):
        reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        reserva(fecha=MANANA, inicio="10:00", fin="11:00", estado=EstadoReserva.CONFIRMADA)
        data = api.get(DASHBOARD).data
        assert len(data["solicitudes_por_aprobar"]) == 1
        assert data["proximos_partidos"][0]["estado_pago"] == EstadoPago.PENDIENTE

    def test_expira_antes_de_responder(self, api, cancha_full, reserva):
        r = reserva(fecha=AYER, inicio="08:00", fin="09:00", estado=EstadoReserva.CONFIRMADA)
        api.get(DASHBOARD)
        r.refresh_from_db()
        assert r.estado_reserva == EstadoReserva.FINALIZADA


@pytest.mark.django_db
class TestSummary:
    def test_period_day(self, api, cancha_full, reserva):
        reserva(
            fecha=HOY,
            inicio="08:00",
            fin="09:00",
            estado=EstadoReserva.CONFIRMADA,
            pago=EstadoPago.PAGADO,
            fecha_pago=timezone.now(),
        )
        resp = api.get(SUMMARY, {"period": "day"})
        assert resp.status_code == 200
        assert resp.data["ingresos_recibidos"] == "60000.00"
        assert resp.data["total_reservas"] == 1

    def test_custom_requiere_fechas(self, api, cancha_full):
        assert api.get(SUMMARY, {"period": "custom"}).status_code == 400

    def test_custom_valido(self, api, cancha_full, reserva):
        reserva(fecha=AYER, inicio="08:00", fin="09:00", estado=EstadoReserva.CONFIRMADA)
        resp = api.get(SUMMARY, {"period": "custom", "start": str(AYER), "end": str(HOY)})
        assert resp.status_code == 200
        assert resp.data["dinero_pendiente"] == "60000.00"
        assert len(resp.data["historial"]) == 1

    def test_period_invalido_400(self, api, cancha_full):
        assert api.get(SUMMARY, {"period": "year"}).status_code == 400
