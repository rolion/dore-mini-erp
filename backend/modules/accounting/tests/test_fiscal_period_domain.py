"""CONT-10: agregado FiscalPeriod (INV-01..05; AC-02, AC-05)."""
from datetime import date, datetime, timezone
from unittest import TestCase

from modules.accounting.domain.fiscal_period import (
    CLOSED,
    OPEN,
    FiscalPeriod,
    FiscalPeriodConflict,
    FiscalPeriodValidationError,
)

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)


def period(start=date(2026, 1, 1), end=date(2026, 12, 31), name='2026'):
    return FiscalPeriod.create(name, start, end)


class FiscalPeriodDomainTests(TestCase):
    def test_new_period_is_open_and_trims_the_name(self):  # AC-01, INV-04
        created = period(name='  Año 2026 ')
        self.assertEqual((created.name, created.status), ('Año 2026', OPEN))

    def test_a_single_day_period_is_valid(self):  # EDGE
        self.assertTrue(period(date(2026, 5, 1), date(2026, 5, 1)).contains(date(2026, 5, 1)))

    def test_rejects_start_after_end(self):  # AC-02, INV-02
        with self.assertRaises(FiscalPeriodValidationError) as ctx:
            period(date(2026, 2, 1), date(2026, 1, 1))
        self.assertIn('end_date', ctx.exception.errors)

    def test_rejects_invalid_dates_and_names(self):  # AC-02, INV-01
        for args in (('x', '2026-01-01', date(2026, 1, 2)), ('x', date(2026, 1, 1), None),
                     ('x', datetime(2026, 1, 1), date(2026, 1, 2)), ('', date(2026, 1, 1), date(2026, 1, 2)),
                     ('n' * 81, date(2026, 1, 1), date(2026, 1, 2))):
            with self.assertRaises(FiscalPeriodValidationError):
                FiscalPeriod.create(*args)

    def test_overlap_is_inclusive(self):  # INV-03
        p = period(date(2026, 1, 1), date(2026, 1, 31))
        self.assertTrue(p.overlaps(date(2026, 1, 31), date(2026, 2, 28)))
        self.assertTrue(p.overlaps(date(2025, 12, 1), date(2026, 1, 1)))
        self.assertFalse(p.overlaps(date(2026, 2, 1), date(2026, 2, 28)))

    def test_close_and_reopen_record_who_and_when(self):  # AC-05
        p = period()
        p.close('Ana', NOW)
        self.assertEqual((p.status, p.closed_by_name, p.closed_at), (CLOSED, 'Ana', NOW))
        p.reopen('Beto', NOW)
        self.assertEqual((p.status, p.reopened_by_name), (OPEN, 'Beto'))

    def test_invalid_transitions_are_conflicts(self):  # AC-05, INV-04
        p = period()
        with self.assertRaises(FiscalPeriodConflict) as ctx:
            p.reopen('Ana', NOW)
        self.assertEqual(ctx.exception.code, 'period_invalid_state')
        p.close('Ana', NOW)
        with self.assertRaises(FiscalPeriodConflict) as ctx:
            p.close('Ana', NOW)
        self.assertEqual(ctx.exception.code, 'period_invalid_state')

    def test_a_closed_period_is_immutable(self):  # INV-05
        p = period()
        p.close('Ana', NOW)
        with self.assertRaises(FiscalPeriodConflict) as ctx:
            p.rename('Otro')
        self.assertEqual(ctx.exception.code, 'period_closed')
        with self.assertRaises(FiscalPeriodConflict):
            p.change_limits(date(2026, 1, 1), date(2026, 6, 30))
