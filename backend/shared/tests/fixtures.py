"""Fixtures de datos compartidas por los tests (Iteración 1)."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

import pytest
from modules.bookings.models import EstadoPago, EstadoReserva, Reserva
from modules.fields.models import Cancha, HorarioOperacion, ImagenCancha, Tarifa
from modules.users_auth.models import Rol, Usuario


@pytest.fixture
def admin_user(db) -> Usuario:
    return Usuario.objects.create(
        supabase_uid=uuid.uuid4(),
        nombre="Admin Cancha",
        correo="admin@canchaya.test",
        telefono="3000000000",
        rol=Rol.ADMINISTRADOR,
    )


@pytest.fixture
def cliente(db) -> Usuario:
    return Usuario.objects.create(
        supabase_uid=uuid.uuid4(),
        nombre="Cliente Uno",
        correo="cliente@canchaya.test",
        telefono="3111111111",
        rol=Rol.CLIENTE,
    )


@pytest.fixture
def cancha(admin_user) -> Cancha:
    return Cancha.objects.create(
        id_administrador=admin_user,
        nombre="Cancha Norte",
        direccion="Cra 1 # 2-3",
        zona="Norte",
        descripcion="Sintética",
        precio_base=Decimal("60000.00"),
        estado=True,
    )


@pytest.fixture
def horario(cancha):
    def _make(dia=1, abre="08:00", cierra="12:00", activo=True):
        return HorarioOperacion.objects.create(
            id_cancha=cancha,
            dia_semana=dia,
            hora_apertura=dt.time.fromisoformat(abre),
            hora_cierre=dt.time.fromisoformat(cierra),
            activo=activo,
        )

    return _make


@pytest.fixture
def tarifa(cancha):
    def _make(*, dia=None, fecha=None, inicio="08:00", fin="10:00", precio="70000.00"):
        return Tarifa.objects.create(
            id_cancha=cancha,
            dia_semana=dia,
            fecha_especial=fecha,
            hora_inicio=dt.time.fromisoformat(inicio),
            hora_fin=dt.time.fromisoformat(fin),
            precio_hora=Decimal(precio),
        )

    return _make


@pytest.fixture
def imagen(cancha):
    def _make(principal=False, url=None):
        return ImagenCancha.objects.create(
            id_cancha=cancha,
            url_imagen=url or f"https://storage.test/img-{uuid.uuid4().hex}.jpg",
            descripcion="foto",
            imagen_principal=principal,
        )

    return _make


@pytest.fixture
def reserva(cancha, cliente):
    def _make(
        *,
        codigo=None,
        fecha=None,
        inicio="08:00",
        fin="09:00",
        estado=EstadoReserva.PENDIENTE,
        pago=EstadoPago.PENDIENTE,
        fecha_pago=None,
        precio="60000.00",
    ):
        codigo = codigo or f"CY-240801-{uuid.uuid4().hex[:4].upper()}"
        return Reserva.objects.create(
            codigo_reserva=codigo,
            id_cancha=cancha,
            id_cliente=cliente,
            nombre_cliente=cliente.nombre,
            correo_cliente=cliente.correo,
            telefono_cliente=cliente.telefono,
            fecha_reserva=fecha or dt.date(2026, 12, 1),
            hora_inicio=dt.time.fromisoformat(inicio),
            hora_fin=dt.time.fromisoformat(fin),
            precio_total=Decimal(precio),
            estado_reserva=estado,
            estado_pago=pago,
            fecha_pago=fecha_pago,
        )

    return _make
