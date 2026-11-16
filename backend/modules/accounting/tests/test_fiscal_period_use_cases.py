"""CONT-10: casos de uso de períodos con un repositorio en memoria y un puerto de uso simulado (AC-03, AC-08)."""
from datetime import date, datetime, timezone
from unittest import TestCase
from uuid import uuid4

from modules.accounting.application.fiscal_periods import (
    CloseFiscalPeriod,
    CreateFiscalPeriod,
    ReopenFiscalPeriod,
    UpdateFiscalPeriod,
)
from modules.accounting.domain.fiscal_period import FiscalPeriodConflict, FiscalPeriodNotFound

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)


class InMemoryPeriods:
    def __init__(self):
        self.company_id = uuid4()
        self.rows = {}
        self.locked = 0

    def lock_company(self):
        self.locked += 1

    def all(self):
        return sorted(self.rows.values(), key=lambda p: p.start_date, reverse=True)

    def get(self, period_id):
        return self.rows.get(period_id)

    get_for_update = get

    def overlapping(self, start, end, exclude_id=None):
        return [p for p in self.rows.values() if p.id != exclude_id and p.overlaps(start, end)]

    def save(self, period):
        self.rows[period.id] = period
        return period


class FakeUsage:
    def __init__(self, outside=0):
        self.outside = outside
        self.calls = []

    def entries_outside(self, company_id, period_id, start_date, end_date):
        self.calls.append((company_id, period_id, start_date, end_date))
        return self.outside


class FiscalPeriodUseCaseTests(TestCase):
    def setUp(self):
        self.periods = InMemoryPeriods()
        self.q1 = CreateFiscalPeriod(self.periods).execute('Q1', date(2026, 1, 1), date(2026, 3, 31))

    def test_create_serializes_the_company_and_reports_every_overlapping_period(self):  # AC-03
        CreateFiscalPeriod(self.periods).execute('Q2', date(2026, 4, 1), date(2026, 6, 30))
        with self.assertRaises(FiscalPeriodConflict) as ctx:
            CreateFiscalPeriod(self.periods).execute('Largo', date(2026, 3, 1), date(2026, 4, 30))
        self.assertEqual((ctx.exception.code, sorted(ctx.exception.periods)), ('period_overlap', ['Q1', 'Q2']))
        self.assertEqual(self.periods.locked, 3)
        self.assertEqual(len(self.periods.all()), 2)

    def test_changing_limits_checks_overlap_ignoring_itself(self):  # AC-03
        updated = UpdateFiscalPeriod(self.periods, FakeUsage()).execute(self.q1.id, end_date=date(2026, 2, 28))
        self.assertEqual(updated.end_date, date(2026, 2, 28))
        CreateFiscalPeriod(self.periods).execute('Q2', date(2026, 4, 1), date(2026, 6, 30))
        with self.assertRaises(FiscalPeriodConflict) as ctx:
            UpdateFiscalPeriod(self.periods, FakeUsage()).execute(self.q1.id, end_date=date(2026, 4, 1))
        self.assertEqual(ctx.exception.code, 'period_overlap')

    def test_blocks_limits_that_would_leave_entries_outside(self):  # AC-08
        usage = FakeUsage(outside=3)
        with self.assertRaises(FiscalPeriodConflict) as ctx:
            UpdateFiscalPeriod(self.periods, usage).execute(self.q1.id, start_date=date(2026, 2, 1))
        self.assertEqual(ctx.exception.code, 'period_has_entries')
        self.assertEqual(usage.calls, [(self.periods.company_id, self.q1.id, date(2026, 2, 1), date(2026, 3, 31))])

    def test_allows_limits_when_entries_stay_covered_and_skips_the_check_without_a_limits_change(self):  # AC-08
        usage = FakeUsage(outside=0)
        UpdateFiscalPeriod(self.periods, usage).execute(self.q1.id, end_date=date(2026, 6, 30))
        self.assertEqual(len(usage.calls), 1)
        UpdateFiscalPeriod(self.periods, usage).execute(self.q1.id, name='Primer trimestre')
        UpdateFiscalPeriod(self.periods, usage).execute(self.q1.id, start_date=date(2026, 1, 1))  # mismo valor
        self.assertEqual(len(usage.calls), 1)
        self.assertEqual(self.periods.get(self.q1.id).name, 'Primer trimestre')

    def test_close_and_reopen_only_change_the_state(self):  # AC-05, INV-07
        closed = CloseFiscalPeriod(self.periods).execute(self.q1.id, 'Ana', NOW)
        self.assertFalse(closed.is_open)
        with self.assertRaises(FiscalPeriodConflict) as ctx:
            UpdateFiscalPeriod(self.periods, FakeUsage()).execute(self.q1.id, name='x')
        self.assertEqual(ctx.exception.code, 'period_closed')
        self.assertTrue(ReopenFiscalPeriod(self.periods).execute(self.q1.id, 'Beto', NOW).is_open)

    def test_unknown_period_is_not_found(self):
        with self.assertRaises(FiscalPeriodNotFound):
            CloseFiscalPeriod(self.periods).execute(uuid4(), 'Ana', NOW)
