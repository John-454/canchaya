"""T3.2 — Motor de tarifas: prioridad, bloques alineados (R4) y huecos (R10)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from shared.exceptions import (
    BLOQUE_NO_ALINEADO,
    DURACION_INVALIDA,
    FUERA_DE_HORARIO,
    BusinessRuleViolation,
)

from modules.fields.models import HorarioOperacion, Tarifa
from modules.fields.services_pricing import (
    ORIGEN_BASE,
    ORIGEN_ESPECIAL,
    ORIGEN_SEMANAL,
    calcular_precio,
    tarifar_fecha,
)

# 2026-12-01 = martes (dia_semana 2).  2026-12-24 = jueves (4).
MARTES = dt.date(2026, 12, 1)
JUEVES_24 = dt.date(2026, 12, 24)
DOMINGO = dt.date(2026, 12, 6)


def _h(texto: str) -> dt.time:
    return dt.time.fromisoformat(texto)


@pytest.fixture
def cancha_semana(cancha):
    """Lunes a viernes, 08-12 y 13-22."""
    for dia in range(1, 6):
        HorarioOperacion.objects.create(
            id_cancha=cancha,
            dia_semana=dia,
            hora_apertura=_h("08:00"),
            hora_cierre=_h("12:00"),
        )
        HorarioOperacion.objects.create(
            id_cancha=cancha,
            dia_semana=dia,
            hora_apertura=_h("13:00"),
            hora_cierre=_h("22:00"),
        )
    return cancha


class TestPrioridad:
    def test_precio_base_cuando_no_hay_tarifa(self, cancha_semana):
        bloques = tarifar_fecha(cancha_semana, MARTES)
        assert len(bloques) == 4 + 9
        assert {b.origen for b in bloques} == {ORIGEN_BASE}
        assert bloques[0].precio == Decimal("60000.00")

    def test_tarifa_semanal_pisa_al_base(self, cancha_semana):
        Tarifa.objects.create(
            id_cancha=cancha_semana,
            dia_semana=2,
            hora_inicio=_h("08:00"),
            hora_fin=_h("10:00"),
            precio_hora=Decimal("80000"),
        )
        bloques = {b.hora_inicio: b for b in tarifar_fecha(cancha_semana, MARTES)}
        assert bloques[_h("08:00")].origen == ORIGEN_SEMANAL
        assert bloques[_h("08:00")].precio == Decimal("80000")
        assert bloques[_h("10:00")].origen == ORIGEN_BASE

    def test_no_aplica_en_otro_dia(self, cancha_semana):
        Tarifa.objects.create(
            id_cancha=cancha_semana,
            dia_semana=3,
            hora_inicio=_h("08:00"),
            hora_fin=_h("12:00"),
            precio_hora=Decimal("99999"),
        )
        assert {b.origen for b in tarifar_fecha(cancha_semana, MARTES)} == {ORIGEN_BASE}

    def test_fecha_especial_pisa_a_la_semanal(self, cancha_semana):
        Tarifa.objects.create(
            id_cancha=cancha_semana,
            dia_semana=4,
            hora_inicio=_h("08:00"),
            hora_fin=_h("12:00"),
            precio_hora=Decimal("70000"),
        )
        Tarifa.objects.create(
            id_cancha=cancha_semana,
            fecha_especial=JUEVES_24,
            hora_inicio=_h("09:00"),
            hora_fin=_h("11:00"),
            precio_hora=Decimal("95000"),
        )
        bloques = {b.hora_inicio: b for b in tarifar_fecha(cancha_semana, JUEVES_24)}
        assert bloques[_h("08:00")].origen == ORIGEN_SEMANAL
        assert bloques[_h("09:00")].origen == ORIGEN_ESPECIAL
        assert bloques[_h("09:00")].precio == Decimal("95000")
        assert bloques[_h("11:00")].origen == ORIGEN_SEMANAL

    def test_tarifa_inactiva_se_ignora(self, cancha_semana):
        Tarifa.objects.create(
            id_cancha=cancha_semana,
            dia_semana=2,
            hora_inicio=_h("08:00"),
            hora_fin=_h("12:00"),
            precio_hora=Decimal("1"),
            activo=False,
        )
        assert {b.origen for b in tarifar_fecha(cancha_semana, MARTES)} == {ORIGEN_BASE}

    def test_fecha_sin_horario_no_tiene_bloques(self, cancha_semana):
        assert tarifar_fecha(cancha_semana, DOMINGO) == []


class TestSumaDeBloques:
    def test_dos_horas_sumando(self, cancha_semana):
        Tarifa.objects.create(
            id_cancha=cancha_semana,
            dia_semana=2,
            hora_inicio=_h("08:00"),
            hora_fin=_h("09:00"),
            precio_hora=Decimal("70000"),
        )
        total, bloques = calcular_precio(cancha_semana, MARTES, _h("08:00"), _h("10:00"))
        assert [b.origen for b in bloques] == [ORIGEN_SEMANAL, ORIGEN_BASE]
        assert total == Decimal("130000.00")

    def test_rango_de_3_horas(self, cancha_semana):
        total, bloques = calcular_precio(cancha_semana, MARTES, _h("13:00"), _h("16:00"))
        assert len(bloques) == 3
        assert total == Decimal("180000.00")


class TestR4:
    @pytest.mark.parametrize(
        "inicio,fin",
        [(_h("08:00"), _h("08:30")), (_h("08:15"), _h("09:00")), (_h("08:00"), _h("09:45"))],
    )
    def test_bloques_no_alineados(self, cancha_semana, inicio, fin):
        with pytest.raises(BusinessRuleViolation) as exc:
            calcular_precio(cancha_semana, MARTES, inicio, fin)
        assert exc.value.code in {BLOQUE_NO_ALINEADO, DURACION_INVALIDA}

    def test_duracion_menor_a_60(self, cancha_semana):
        with pytest.raises(BusinessRuleViolation) as exc:
            calcular_precio(cancha_semana, MARTES, _h("08:00"), _h("08:00"))
        assert exc.value.code == DURACION_INVALIDA

    def test_una_hora_exacta_es_valida(self, cancha_semana):
        total, bloques = calcular_precio(cancha_semana, MARTES, _h("08:00"), _h("09:00"))
        assert len(bloques) == 1
        assert total == Decimal("60000.00")


class TestR10HuecosYFueraDeHorario:
    def test_rango_que_cruza_el_hueco(self, cancha_semana):
        """08-12 y 13-22: una reserva 11:00-14:00 cae en el hueco."""
        with pytest.raises(BusinessRuleViolation) as exc:
            calcular_precio(cancha_semana, MARTES, _h("11:00"), _h("14:00"))
        assert exc.value.code == FUERA_DE_HORARIO

    def test_rango_antes_de_abrir(self, cancha_semana):
        with pytest.raises(BusinessRuleViolation) as exc:
            calcular_precio(cancha_semana, MARTES, _h("07:00"), _h("09:00"))
        assert exc.value.code == FUERA_DE_HORARIO

    def test_rango_que_pasa_del_cierre(self, cancha_semana):
        with pytest.raises(BusinessRuleViolation):
            calcular_precio(cancha_semana, MARTES, _h("21:00"), _h("23:00"))

    def test_dia_sin_operacion(self, cancha_semana):
        with pytest.raises(BusinessRuleViolation) as exc:
            calcular_precio(cancha_semana, DOMINGO, _h("08:00"), _h("09:00"))
        assert exc.value.code == FUERA_DE_HORARIO

    def test_franja_inactiva_no_cuenta(self, cancha_semana):
        cancha_semana.horarios.filter(hora_apertura=_h("13:00")).update(activo=False)
        with pytest.raises(BusinessRuleViolation):
            calcular_precio(cancha_semana, MARTES, _h("13:00"), _h("14:00"))

    def test_rango_completo_en_una_franja(self, cancha_semana):
        total, bloques = calcular_precio(cancha_semana, MARTES, _h("08:00"), _h("12:00"))
        assert len(bloques) == 4
        assert total == Decimal("240000.00")
