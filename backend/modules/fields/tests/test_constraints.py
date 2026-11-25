"""T1.11 — Constraints de `canchas`, `imagenes_cancha`, `horarios_operacion`, `tarifas`."""

from __future__ import annotations

import datetime as dt

import pytest
from django.db import IntegrityError, transaction


class TestCancha:
    def test_administrador_tiene_una_sola_cancha(self, cancha):
        from modules.fields.models import Cancha

        with pytest.raises(IntegrityError), transaction.atomic():
            Cancha.objects.create(
                id_administrador=cancha.id_administrador,
                nombre="Duplicada",
                direccion="x",
            )

    def test_precio_base_negativo_rechazado(self, admin_user):
        from modules.fields.models import Cancha

        with pytest.raises(IntegrityError), transaction.atomic():
            Cancha.objects.create(
                id_administrador=admin_user,
                nombre="Neg",
                direccion="x",
                precio_base="-1",
            )


class TestImagenPrincipal:
    def test_solo_una_imagen_principal_por_cancha(self, imagen):
        imagen(principal=True)
        with pytest.raises(IntegrityError), transaction.atomic():
            imagen(principal=True)

    def test_imagen_principal_y_secundarias_conviven(self, imagen):
        imagen(principal=True)
        imagen(principal=False)
        imagen(principal=False)
        from modules.fields.models import ImagenCancha

        assert ImagenCancha.objects.filter(imagen_principal=True).count() == 1

    def test_url_debe_ser_http(self, cancha):
        from modules.fields.models import ImagenCancha

        with pytest.raises(IntegrityError), transaction.atomic():
            ImagenCancha.objects.create(id_cancha=cancha, url_imagen="ftp://nope")


class TestHorariosOperacion:
    def test_solape_mismo_dia_rechazado(self, horario):
        horario(dia=1, abre="08:00", cierra="12:00")
        with pytest.raises(IntegrityError), transaction.atomic():
            horario(dia=1, abre="11:00", cierra="14:00")

    def test_tramos_contiguos_permitidos(self, horario):
        horario(dia=1, abre="08:00", cierra="12:00")
        horario(dia=1, abre="12:00", cierra="14:00")  # contiguo, sin solape
        horario(dia=2, abre="08:00", cierra="15:00")  # otro día
        assert horario(dia=1, abre="15:00", cierra="22:00").pk

    def test_horario_inactivo_no_bloquea(self, horario):
        horario(dia=1, abre="08:00", cierra="12:00", activo=False)
        horario(dia=1, abre="09:00", cierra="11:00")

    def test_apertura_en_punto(self, cancha):
        from modules.fields.models import HorarioOperacion

        with pytest.raises(IntegrityError), transaction.atomic():
            HorarioOperacion.objects.create(
                id_cancha=cancha,
                dia_semana=3,
                hora_apertura=dt.time(8, 30),
                hora_cierre=dt.time(12, 0),
            )

    def test_cierre_antes_de_apertura_rechazado(self, cancha):
        from modules.fields.models import HorarioOperacion

        with pytest.raises(IntegrityError), transaction.atomic():
            HorarioOperacion.objects.create(
                id_cancha=cancha,
                dia_semana=3,
                hora_apertura=dt.time(13),
                hora_cierre=dt.time(12),
            )

    def test_dia_semana_fuera_de_rango(self, cancha):
        from modules.fields.models import HorarioOperacion

        with pytest.raises(IntegrityError), transaction.atomic():
            HorarioOperacion.objects.create(
                id_cancha=cancha, dia_semana=8, hora_apertura=dt.time(8), hora_cierre=dt.time(9)
            )


class TestTarifas:
    def test_semanal_xor_especial(self, tarifa):
        with pytest.raises(IntegrityError), transaction.atomic():
            tarifa(dia=1, fecha=dt.date(2026, 12, 1))
        with pytest.raises(IntegrityError), transaction.atomic():
            tarifa()  # ni día ni fecha

    def test_solape_semanal_rechazado(self, tarifa):
        tarifa(dia=1, inicio="08:00", fin="10:00")
        with pytest.raises(IntegrityError), transaction.atomic():
            tarifa(dia=1, inicio="09:00", fin="11:00")

    def test_semanal_de_otro_dia_no_choca(self, tarifa):
        tarifa(dia=1, inicio="08:00", fin="10:00")
        tarifa(dia=2, inicio="08:00", fin="10:00")

    def test_solape_especial_rechazado(self, tarifa):
        fecha = dt.date(2026, 12, 24)
        tarifa(fecha=fecha, inicio="08:00", fin="12:00")
        with pytest.raises(IntegrityError), transaction.atomic():
            tarifa(fecha=fecha, inicio="10:00", fin="14:00")

    def test_especial_y_semanal_misma_hora_no_chocan(self, tarifa):
        tarifa(dia=4, inicio="08:00", fin="12:00")
        tarifa(fecha=dt.date(2026, 12, 24), inicio="08:00", fin="12:00")

    def test_precio_positivo(self, tarifa):
        with pytest.raises(IntegrityError), transaction.atomic():
            tarifa(dia=5, inicio="08:00", fin="09:00", precio="0")

    def test_tarifa_inactiva_no_bloquea(self, cancha, tarifa):
        from decimal import Decimal

        from modules.fields.models import Tarifa

        Tarifa.objects.create(
            id_cancha=cancha,
            dia_semana=1,
            hora_inicio=dt.time(8),
            hora_fin=dt.time(10),
            precio_hora=Decimal("50000"),
            activo=False,
        )
        tarifa(dia=1, inicio="08:00", fin="10:00")
