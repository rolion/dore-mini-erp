"""CONT-10: serialización de cierre y contabilización, y de altas solapadas (AC-09)."""
import time
from datetime import date, datetime, timezone

from django.test import TransactionTestCase

from modules.accounting import services
from modules.accounting.application.fiscal_periods import CloseFiscalPeriod, CreateFiscalPeriod
from modules.accounting.domain.fiscal_period import FiscalPeriodClosed, FiscalPeriodConflict
from modules.accounting.infrastructure.django.models import FiscalPeriodModel
from modules.accounting.infrastructure.django.repositories import DjangoFiscalPeriodRepository
from modules.accounting.tests.test_concurrency import _run_together
from modules.accounts.testing import make_company

DAY = date(2026, 5, 10)


class CloseVsPostingTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('A')
        self.repo = DjangoFiscalPeriodRepository(self.company.id)
        self.period = CreateFiscalPeriod(self.repo).execute('Q2', date(2026, 4, 1), date(2026, 6, 30))
        self.events = []

    def post(self, hold: float = 0.0):
        def job():
            services.lock_open_period(self.company.id, DAY)
            time.sleep(hold)  # el asiento se «inserta» mientras sostiene el bloqueo del período
            self.events.append('posted')
        return job

    def close(self, delay: float = 0.0):
        def job():
            time.sleep(delay)
            CloseFiscalPeriod(self.repo).execute(self.period.id, 'Ana', datetime(2026, 5, 11, tzinfo=timezone.utc))
            self.events.append('closed')
        return job

    def test_closing_waits_for_the_posting_in_flight(self):  # AC-09
        outcomes = _run_together(self.post(hold=0.6), self.close(delay=0.2))
        self.assertEqual(outcomes, [None, None])
        self.assertEqual(self.events, ['posted', 'closed'])

    def test_a_posting_that_starts_after_the_close_is_rejected(self):  # AC-09
        outcomes = _run_together(self.close(), self.post(hold=0.0))
        # Con salida en carrera pura: o el asiento entró antes del cierre, o se rechazó; nunca después.
        if self.events == ['closed']:
            self.assertIsInstance(outcomes[1], FiscalPeriodClosed)
        else:
            self.assertEqual(self.events, ['posted', 'closed'])
        self.assertEqual(FiscalPeriodModel.objects.get(pk=self.period.id).status, 'CLOSED')

    def test_a_posting_after_a_committed_close_is_rejected(self):  # AC-09
        _run_together(self.close())
        outcomes = _run_together(self.post())
        self.assertIsInstance(outcomes[0], FiscalPeriodClosed)
        self.assertEqual(self.events, ['closed'])


class OverlappingCreationTests(TransactionTestCase):
    def test_two_simultaneous_overlapping_creations_leave_one_period(self):  # AC-09, INV-03
        company = make_company('A')

        def create(name):
            return lambda: CreateFiscalPeriod(DjangoFiscalPeriodRepository(company.id)).execute(
                name, date(2026, 1, 1), date(2026, 3, 31))

        outcomes = _run_together(create('Uno'), create('Dos'))
        self.assertEqual(sorted(o is None for o in outcomes), [False, True])
        self.assertTrue(any(isinstance(o, FiscalPeriodConflict) for o in outcomes))
        self.assertEqual(FiscalPeriodModel.objects.filter(company_id=company.id).count(), 1)

    def test_different_companies_do_not_block_each_other_and_may_repeat_ranges(self):  # AC-04
        a, b = make_company('A'), make_company('B')
        outcomes = _run_together(
            lambda: CreateFiscalPeriod(DjangoFiscalPeriodRepository(a.id)).execute('P', date(2026, 1, 1), date(2026, 3, 31)),
            lambda: CreateFiscalPeriod(DjangoFiscalPeriodRepository(b.id)).execute('P', date(2026, 1, 1), date(2026, 3, 31)))
        self.assertEqual(outcomes, [None, None])
