"""T1.11 — Constraints de `reservas` y `usuarios`."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.bookings.models import EstadoPago, EstadoReserva


class TestSolapeReservas:
    def test_dos_reservas_pendientes_no_se_solapan(self, reserva):
        reserva(inicio="08:00", fin="10:00")
        with pytest.raises(IntegrityError), transaction.atomic():
            reserva(inicio="09:00", fin="11:00")

    def test_confirmada_y_pendiente_no_se_solapan(self, reserva):
        reserva(inicio="08:00", fin="10:00", estado=EstadoReserva.CONFIRMADA)
        with pytest.raises(IntegrityError), transaction.atomic():
            reserva(inicio="09:00", fin="10:00")

    def test_bloques_contiguos_permitidos(self, reserva):
        reserva(inicio="08:00", fin="09:00", codigo="CY-240801-AAAA")
        reserva(inicio="09:00", fin="10:00", codigo="CY-240801-BBBB")

    def test_cancelada_libera_el_horario(self, reserva):
        reserva(inicio="08:00", fin="10:00", estado=EstadoReserva.CANCELADA)
        reserva(inicio="08:00", fin="10:00")

    def test_finalizada_no_bloquea(self, reserva):
        reserva(
            inicio="08:00",
            fin="10:00",
            estado=EstadoReserva.FINALIZADA,
            pago=EstadoPago.PAGADO,
            fecha_pago=timezone.now(),
        )
        reserva(inicio="08:00", fin="10:00")

    def test_otra_fecha_no_choca(self, reserva):
        reserva(fecha=dt.date(2026, 12, 1), inicio="08:00", fin="10:00")
        reserva(fecha=dt.date(2026, 12, 2), inicio="08:00", fin="10:00")


class TestDatosReserva:
    def test_pagado_exige_fecha_pago(self, reserva):
        with pytest.raises(IntegrityError), transaction.atomic():
            reserva(pago=EstadoPago.PAGADO, fecha_pago=None)

    def test_pendiente_no_admite_fecha_pago(self, reserva):
        with pytest.raises(IntegrityError), transaction.atomic():
            reserva(pago=EstadoPago.PENDIENTE, fecha_pago=timezone.now())

    def test_pagado_con_fecha_ok(self, reserva):
        r = reserva(pago=EstadoPago.PAGADO, fecha_pago=timezone.now())
        assert r.estado_pago == EstadoPago.PAGADO

    def test_estado_reserva_invalido(self, reserva):
        with pytest.raises(IntegrityError), transaction.atomic():
            reserva(estado="Talvez")

    def test_horas_en_punto_obligatorias(self, cancha, cliente):
        from decimal import Decimal

        from modules.bookings.models import Reserva

        with pytest.raises(IntegrityError), transaction.atomic():
            Reserva.objects.create(
                codigo_reserva="CY-240801-CCCC",
                id_cancha=cancha,
                id_cliente=cliente,
                nombre_cliente="x",
                correo_cliente="x@x.test",
                telefono_cliente="300",
                fecha_reserva=dt.date(2026, 12, 5),
                hora_inicio=dt.time(8, 15),
                hora_fin=dt.time(9, 0),
                precio_total=Decimal("1"),
            )

    def test_formato_codigo_reserva(self, reserva):
        with pytest.raises(IntegrityError), transaction.atomic():
            reserva(codigo="ABC")

    def test_codigo_reserva_unico(self, reserva):
        reserva(codigo="CY-240801-DDDD")
        with pytest.raises(IntegrityError), transaction.atomic():
            reserva(codigo="CY-240801-DDDD", inicio="11:00", fin="12:00")


class TestUsuarios:
    def test_telefono_nullable_para_google(self, db):
        from modules.users_auth.models import Rol, Usuario

        u = Usuario.objects.create(
            supabase_uid=uuid.uuid4(), nombre="Google User", correo="g@canchaya.test"
        )
        assert u.telefono is None
        assert u.rol == Rol.CLIENTE
        assert u.requiere_telefono is True

    def test_correo_unico(self, cliente):
        from modules.users_auth.models import Usuario

        with pytest.raises(IntegrityError), transaction.atomic():
            Usuario.objects.create(supabase_uid=uuid.uuid4(), nombre="Otro", correo=cliente.correo)

    def test_supabase_uid_unico(self, cliente):
        from modules.users_auth.models import Usuario

        with pytest.raises(IntegrityError), transaction.atomic():
            Usuario.objects.create(
                supabase_uid=cliente.supabase_uid, nombre="Otro", correo="otro@canchaya.test"
            )

    def test_rol_invalido(self, db):
        from modules.users_auth.models import Usuario

        with pytest.raises(IntegrityError), transaction.atomic():
            Usuario.objects.create(
                supabase_uid=uuid.uuid4(), nombre="X", correo="x@canchaya.test", rol="super"
            )

    def test_no_se_borra_cliente_con_reservas(self, reserva, cliente):
        from django.db import IntegrityError, transaction

        reserva()
        # Fase 1: la FK es ON DELETE RESTRICT a nivel PostgreSQL.
        with pytest.raises(IntegrityError), transaction.atomic():
            cliente.delete()
