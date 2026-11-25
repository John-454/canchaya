import datetime as dt

import pytest

from shared.dates import Slot, day_bounds, month_bounds, today_in_tz, week_bounds
from shared.exceptions import BLOQUE_NO_ALINEADO, DURACION_INVALIDA, BusinessRuleViolation
from shared.validators import assert_valid_booking_range, blocks_of, is_aligned_time


class TestAlineacionR4:
    @pytest.mark.parametrize("value", [dt.time(0, 0), dt.time(8, 0), dt.time(22, 0), dt.time(23)])
    def test_horas_en_punto(self, value):
        assert is_aligned_time(value)

    @pytest.mark.parametrize("value", [dt.time(8, 30), dt.time(8, 0, 1)])
    def test_horas_no_alineadas(self, value):
        assert not is_aligned_time(value)

    @pytest.mark.parametrize(
        "inicio,fin",
        [(dt.time(8), dt.time(9)), (dt.time(8), dt.time(12)), (dt.time(21), dt.time(23))],
    )
    def test_duraciones_validas(self, inicio, fin):
        assert_valid_booking_range(inicio, fin)

    def test_duracion_menor_a_60(self):
        with pytest.raises(BusinessRuleViolation) as exc:
            assert_valid_booking_range(dt.time(8), dt.time(8, 30))
        assert exc.value.code == BLOQUE_NO_ALINEADO  # se valida el fin antes

    def test_duracion_cero(self):
        with pytest.raises(BusinessRuleViolation) as exc:
            assert_valid_booking_range(dt.time(8), dt.time(8))
        assert exc.value.code == DURACION_INVALIDA

    def test_bloques(self):
        assert list(blocks_of(dt.time(8), dt.time(11))) == [
            (dt.time(8), dt.time(9)),
            (dt.time(9), dt.time(10)),
            (dt.time(10), dt.time(11)),
        ]


class TestBounds:
    def test_day_bounds(self):
        start, end = day_bounds(dt.date(2026, 12, 1))
        assert start.date() == dt.date(2026, 12, 1)
        assert end - start == dt.timedelta(days=1)

    def test_week_bounds_iso(self):
        start, end = week_bounds(dt.date(2026, 12, 2))  # miércoles
        assert start.date().isoweekday() == 1
        assert (start.date()).isoformat() == "2026-11-30"
        assert end - start == dt.timedelta(days=7)

    def test_month_bounds(self):
        start, end = month_bounds(dt.date(2026, 12, 15))
        assert start.date().isoformat() == "2026-12-01"
        assert end.date().isoformat() == "2027-01-01"

    def test_today_in_tz(self):
        assert today_in_tz() == dt.date.today()

    def test_slot_key(self):
        assert Slot(dt.time(8), dt.time(9)).clave == "08:00-09:00"
