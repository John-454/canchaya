"""T4.1 – T4.3 — Expiración, estados, pago y creación de reservas."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from unittest import mock

import pytest
from django.utils import timezone
from shared.exceptions import (
    ESTADO_INVALIDO,
    HORARIO_NO_DISPONIBLE,
    TELEFONO_REQUERIDO,
    BusinessRuleViolation,
    ConflictError,
)

from modules.bookings.models import EstadoPago, EstadoReserva
from modules.bookings.services import (
    DatosReserva,
    approve,
    cancel,
    create_booking,
    expire_confirmed_bookings,
    generar_codigo_reserva,
    mark_paid,
)
from modules.fields.models import HorarioOperacion
from modules.users_auth.models import Usuario

MANANA = timezone.localdate() + dt.timedelta(days=1)
AYER = timezone.localdate() - dt.timedelta(days=1)


def _h(t: str) -> dt.time:
    return dt.time.fromisoformat(t)


@pytest.fixture
def cancha_con_horario(cancha):
    for dia in range(1, 8):
        HorarioOperacion.objects.create(
            id_cancha=cancha, dia_semana=dia, hora_apertura=_h("08:00"), hora_cierre=_h("22:00")
        )
    return cancha


class TestCodigoReserva:
    def test_formato(self):
        codigo = generar_codigo_reserva(dt.date(2026, 12, 1))
        assert codigo.startswith("CY-261201-")
        assert len(codigo) == 14

    def test_es_aleatorio(self):
        codigos = {generar_codigo_reserva(dt.date(2026, 12, 1)) for _ in range(50)}
        assert len(codigos) > 45


class TestExpiracion:
    def test_confirmada_vencida_pasa_a_finalizada(self, cancha_con_horario, reserva):
        r = reserva(
            fecha=AYER,
            inicio="08:00",
            fin="09:00",
            estado=EstadoReserva.CONFIRMADA,
        )
        assert expire_confirmed_bookings(cancha_con_horario) == 1
        r.refresh_from_db()
        assert r.estado_reserva == EstadoReserva.FINALIZADA

    def test_confirmada_futura_no_expira(self, cancha_con_horario, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00", estado=EstadoReserva.CONFIRMADA)
        assert expire_confirmed_bookings(cancha_con_horario) == 0
        r.refresh_from_db()
        assert r.estado_reserva == EstadoReserva.CONFIRMADA

    def test_pendiente_vencida_no_se_finaliza(self, cancha_con_horario, reserva):
        r = reserva(fecha=AYER, inicio="08:00", fin="09:00", estado=EstadoReserva.PENDIENTE)
        expire_confirmed_bookings(cancha_con_horario)
        r.refresh_from_db()
        assert r.estado_reserva == EstadoReserva.PENDIENTE

    def test_hoy_ya_terminada(self, cancha_con_horario, reserva):
        """Hoy, con hora_fin anterior a 'ahora' (reloj simulado)."""
        hoy = timezone.localdate()
        r = reserva(fecha=hoy, inicio="08:00", fin="09:00", estado=EstadoReserva.CONFIRMADA)
        ahora = timezone.make_aware(dt.datetime.combine(hoy, _h("12:00")))
        with mock.patch("modules.bookings.services.now_in_tz", return_value=ahora):
            assert expire_confirmed_bookings(cancha_con_horario) == 1
        r.refresh_from_db()
        assert r.estado_reserva == EstadoReserva.FINALIZADA

    def test_hoy_aun_no_terminada(self, cancha_con_horario, reserva):
        hoy = timezone.localdate()
        r = reserva(fecha=hoy, inicio="22:00", fin="23:00", estado=EstadoReserva.CONFIRMADA)
        ahora = timezone.make_aware(dt.datetime.combine(hoy, _h("12:00")))
        with mock.patch("modules.bookings.services.now_in_tz", return_value=ahora):
            assert expire_confirmed_bookings(cancha_con_horario) == 0
        r.refresh_from_db()
        assert r.estado_reserva == EstadoReserva.CONFIRMADA

    def test_libera_el_horario(self, cancha_con_horario, reserva, cliente):
        reserva(fecha=AYER, inicio="08:00", fin="10:00", estado=EstadoReserva.CONFIRMADA)
        expire_confirmed_bookings(cancha_con_horario)
        # Finalizada no bloquea: se puede volver a reservar la misma franja
        nueva = ReservaHelper(cancha_con_horario, cliente, AYER, "08:00", "10:00")
        assert nueva.estado_reserva == EstadoReserva.PENDIENTE


def ReservaHelper(cancha, cliente, fecha, inicio, fin):
    return create_booking(
        DatosReserva(
            cancha=cancha,
            cliente_id=cliente.pk,
            fecha_reserva=fecha,
            hora_inicio=_h(inicio),
            hora_fin=_h(fin),
        )
    )


class TestEstados:
    def test_aprobar_pendiente(self, cancha_con_horario, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        assert approve(cancha_con_horario, r.pk).estado_reserva == EstadoReserva.CONFIRMADA

    def test_aprobar_ya_confirmada_409(self, cancha_con_horario, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00", estado=EstadoReserva.CONFIRMADA)
        with pytest.raises(ConflictError) as exc:
            approve(cancha_con_horario, r.pk)
        assert exc.value.code == ESTADO_INVALIDO

    def test_aprobar_cancelada_409(self, cancha_con_horario, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00", estado=EstadoReserva.CANCELADA)
        with pytest.raises(ConflictError):
            approve(cancha_con_horario, r.pk)

    def test_aprobar_finalizada_409(self, cancha_con_horario, reserva):
        r = reserva(
            fecha=MANANA,
            inicio="08:00",
            fin="09:00",
            estado=EstadoReserva.FINALIZADA,
            pago=EstadoPago.PAGADO,
            fecha_pago=timezone.now(),
        )
        with pytest.raises(ConflictError):
            approve(cancha_con_horario, r.pk)

    def test_cancelar_pendiente_y_confirmada(self, cancha_con_horario, reserva):
        a = reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        b = reserva(fecha=MANANA, inicio="10:00", fin="11:00", estado=EstadoReserva.CONFIRMADA)
        assert cancel(cancha_con_horario, a.pk).estado_reserva == EstadoReserva.CANCELADA
        assert cancel(cancha_con_horario, b.pk).estado_reserva == EstadoReserva.CANCELADA

    def test_cancelar_finalizada_409(self, cancha_con_horario, reserva):
        r = reserva(
            fecha=MANANA,
            inicio="08:00",
            fin="09:00",
            estado=EstadoReserva.FINALIZADA,
            pago=EstadoPago.PAGADO,
            fecha_pago=timezone.now(),
        )
        with pytest.raises(ConflictError) as exc:
            cancel(cancha_con_horario, r.pk)
        assert exc.value.code == ESTADO_INVALIDO

    def test_cancelar_con_motivo_anexa_observacion(self, cancha_con_horario, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        cancel(cancha_con_horario, r.pk, "lluvia")
        r.refresh_from_db()
        assert "lluvia" in r.observaciones

    def test_cancelar_libera_el_horario(self, cancha_con_horario, reserva, cliente):
        r = reserva(fecha=MANANA, inicio="08:00", fin="10:00")
        cancel(cancha_con_horario, r.pk)
        nueva = ReservaHelper(cancha_con_horario, cliente, MANANA, "08:00", "10:00")
        assert nueva.estado_reserva == EstadoReserva.PENDIENTE


class TestPago:
    def test_marcar_pagado_registra_fecha(self, cancha_con_horario, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        assert r.fecha_pago is None
        pagada = mark_paid(cancha_con_horario, r.pk)
        assert pagada.estado_pago == EstadoPago.PAGADO
        assert pagada.fecha_pago is not None

    def test_ya_pagada_409(self, cancha_con_horario, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00")
        mark_paid(cancha_con_horario, r.pk)
        with pytest.raises(ConflictError) as exc:
            mark_paid(cancha_con_horario, r.pk)
        assert exc.value.code == "reserva_ya_pagada"

    def test_cancelada_no_se_puede_pagar(self, cancha_con_horario, reserva):
        r = reserva(fecha=MANANA, inicio="08:00", fin="09:00", estado=EstadoReserva.CANCELADA)
        with pytest.raises(ConflictError) as exc:
            mark_paid(cancha_con_horario, r.pk)
        assert exc.value.code == ESTADO_INVALIDO


class TestCreacion:
    def test_precio_calculado_en_backend(self, cancha_con_horario, cliente):
        r = ReservaHelper(cancha_con_horario, cliente, MANANA, "08:00", "10:00")
        assert r.precio_total == Decimal("120000.00")
        assert r.estado_reserva == EstadoReserva.PENDIENTE
        assert r.estado_pago == EstadoPago.PENDIENTE

    def test_snapshot_de_contacto(self, cancha_con_horario, cliente):
        r = ReservaHelper(cancha_con_horario, cliente, MANANA, "08:00", "09:00")
        assert r.nombre_cliente == cliente.nombre
        assert r.telefono_cliente == cliente.telefono

    def test_solape_409(self, cancha_con_horario, cliente):
        ReservaHelper(cancha_con_horario, cliente, MANANA, "08:00", "10:00")
        with pytest.raises(ConflictError) as exc:
            ReservaHelper(cancha_con_horario, cliente, MANANA, "09:00", "11:00")
        assert exc.value.code == HORARIO_NO_DISPONIBLE

    def test_hueco_rechazado_r10(self, cancha_con_horario, cliente):
        cancha_con_horario.horarios.filter(hora_apertura=_h("12:00")).delete()
        HorarioOperacion.objects.filter(id_cancha=cancha_con_horario).update(
            hora_cierre=_h("12:00")
        )
        HorarioOperacion.objects.create(
            id_cancha=cancha_con_horario,
            dia_semana=MANANA.isoweekday(),
            hora_apertura=_h("13:00"),
            hora_cierre=_h("18:00"),
        )
        from shared.exceptions import FUERA_DE_HORARIO

        with pytest.raises(BusinessRuleViolation) as exc:
            ReservaHelper(cancha_con_horario, cliente, MANANA, "11:00", "14:00")
        assert exc.value.code == FUERA_DE_HORARIO

    def test_cliente_sin_telefono_no_puede_reservar(self, cancha_con_horario):
        sin_tel = Usuario.objects.create(
            supabase_uid=uuid.uuid4(), nombre="Google", correo="g2@canchaya.test"
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            ReservaHelper(cancha_con_horario, sin_tel, MANANA, "08:00", "09:00")
        assert exc.value.code == TELEFONO_REQUERIDO

    def test_reintenta_ante_colision_de_codigo(self, cancha_con_horario, cliente):
        fijo = generar_codigo_reserva(MANANA)
        ReservaHelper(cancha_con_horario, cliente, MANANA, "08:00", "09:00")
        from modules.bookings.models import Reserva

        Reserva.objects.update(codigo_reserva=fijo)
        # El primer intento colisiona; el segundo genera otro código.
        with mock.patch(
            "modules.bookings.services.generar_codigo_reserva",
            side_effect=[fijo, fijo, "CY-999999-UNIQ"],
        ):
            r = ReservaHelper(cancha_con_horario, cliente, MANANA, "10:00", "11:00")
        assert r.codigo_reserva == "CY-999999-UNIQ"
