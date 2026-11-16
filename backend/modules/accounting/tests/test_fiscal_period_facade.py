"""CONT-10: contrato `lock_open_period` / `period_for` (AC-06, AC-07)."""
from datetime import date, datetime, timezone

from django.db import transaction
from django.test import TestCase

from modules.accounting import services
from modules.accounting.application.fiscal_periods import CloseFiscalPeriod, CreateFiscalPeriod
from modules.accounting.infrastructure.django.repositories import DjangoFiscalPeriodRepository
from modules.accounts.testing import make_company


class LockOpenPeriodTests(TestCase):
    def setUp(self):
        self.company = make_company('A')
        self.repo = DjangoFiscalPeriodRepository(self.company.id)
        self.q1 = CreateFiscalPeriod(self.repo).execute('Q1', date(2026, 1, 1), date(2026, 3, 31))
        self.q2 = CreateFiscalPeriod(self.repo).execute('Q2', date(2026, 4, 1), date(2026, 6, 30))
        CloseFiscalPeriod(self.repo).execute(self.q1.id, 'Ana', datetime(2026, 4, 2, tzinfo=timezone.utc))

    def test_accepts_a_date_in_an_open_period(self):  # AC-06
        ref = services.lock_open_period(self.company.id, date(2026, 6, 30))
        self.assertEqual((ref.id, ref.name, ref.is_open), (self.q2.id, 'Q2', True))

    def test_rejects_a_date_without_period_and_in_a_closed_period(self):  # AC-06
        with self.assertRaises(services.DateOutsideFiscalPeriod):
            services.lock_open_period(self.company.id, date(2026, 7, 1))
        with self.assertRaises(services.FiscalPeriodClosed) as ctx:
            services.lock_open_period(self.company.id, date(2026, 3, 31))
        self.assertEqual(ctx.exception.name, 'Q1')

    def test_a_reversal_dated_in_an_open_period_is_accepted_although_the_original_is_in_a_closed_one(self):  # AC-06
        self.assertFalse(services.period_for(self.company.id, date(2026, 2, 1)).is_open)
        self.assertEqual(services.lock_open_period(self.company.id, date(2026, 4, 15)).name, 'Q2')

    def test_other_companies_periods_do_not_count(self):  # AC-04
        other = make_company('B')
        with self.assertRaises(services.DateOutsideFiscalPeriod):
            services.lock_open_period(other.id, date(2026, 4, 15))
        self.assertIsNone(services.period_for(other.id, date(2026, 4, 15)))

    def test_period_for_returns_open_and_closed_periods_without_a_transaction_requirement(self):
        self.assertEqual(services.period_for(self.company.id, date(2026, 5, 1)).name, 'Q2')

    def test_rejects_a_non_date(self):
        with self.assertRaises(services.FiscalPeriodContractError):
            services.lock_open_period(self.company.id, datetime(2026, 4, 15))


class LockOutsideTransactionTests(TestCase):
    def test_requires_the_callers_transaction(self):  # AC-07
        company = make_company('A')
        # TestCase ya envuelve cada prueba en una transacción; se simula su ausencia como lo hace `record_entry`.
        from unittest import mock
        with mock.patch.object(services.connection, 'in_atomic_block', False):
            with self.assertRaises(services.FiscalPeriodContractError):
                services.lock_open_period(company.id, date(2026, 4, 15))
        with transaction.atomic():
            with self.assertRaises(services.DateOutsideFiscalPeriod):
                services.lock_open_period(company.id, date(2026, 4, 15))
