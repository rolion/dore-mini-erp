"""CONT-02: concurrencia del motor (AC-03, AC-06, AC-08, AC-09 de CONT-10 con asientos reales)."""
import threading
import time
from datetime import date, datetime, timezone

from django.db import transaction
from django.test import TransactionTestCase

from modules.accounting import services
from modules.accounting.application.fiscal_periods import CloseFiscalPeriod
from modules.accounting.infrastructure.django.models import JournalEntryModel, JournalLineModel
from modules.accounting.infrastructure.django.repositories import DjangoFiscalPeriodRepository
from modules.accounting.tests.journal_support import DAY, automatic, entry_input, make_account, make_period
from modules.accounting.tests.test_concurrency import _run_together
from modules.accounts.testing import make_company


class JournalConcurrencyBase(TransactionTestCase):
    def setUp(self):
        self.company = make_company('A')
        self.cash = make_account(self.company.id, 'Caja')
        self.bank = make_account(self.company.id, 'Banco')
        self.income = make_account(self.company.id, 'Ingresos servicios', 'INCOME')
        self.period = make_period(self.company.id)

    def post(self, **overrides):
        return services.post_journal_entry(self.company.id, entry_input(self.cash, self.bank, self.income, **overrides))


class ConcurrentPostTests(JournalConcurrencyBase):
    def test_concurrent_retries_of_one_event_create_one_entry(self):  # AC-03, INV-07
        origin = automatic()
        results = []
        outcomes = _run_together(*[lambda: results.append(self.post(**origin)) for _ in range(4)])
        self.assertEqual(outcomes, [None] * 4)
        self.assertEqual(sorted(r.created for r in results), [False, False, False, True])
        self.assertEqual(len({r.entry.id for r in results}), 1)
        self.assertEqual((JournalEntryModel.objects.count(), JournalLineModel.objects.count()), (1, 3))

    def test_concurrent_distinct_events_all_persist_without_deadlock(self):  # AC-03
        outcomes = _run_together(*[lambda: self.post(**automatic()) for _ in range(4)])
        self.assertEqual(outcomes, [None] * 4)
        self.assertEqual(JournalEntryModel.objects.count(), 4)


class ConcurrentReverseTests(JournalConcurrencyBase):
    def test_two_simultaneous_reversals_create_one(self):  # AC-06
        with transaction.atomic():
            original = self.post().entry
        results = []
        outcomes = _run_together(*[lambda: results.append(
            services.reverse_journal_entry(self.company.id, original.id, DAY, 'Error')) for _ in range(2)])
        self.assertEqual(outcomes, [None, None])
        self.assertEqual(sorted(r.created for r in results), [False, True])
        self.assertEqual(JournalEntryModel.objects.filter(reverses_id=original.id).count(), 1)


class CloseVsEntryTests(JournalConcurrencyBase):
    def close(self, wait_for: threading.Event):
        def job():
            self.assertTrue(wait_for.wait(timeout=10))
            CloseFiscalPeriod(DjangoFiscalPeriodRepository(self.company.id)).execute(
                self.period.id, 'Ana', datetime(2026, 5, 11, tzinfo=timezone.utc))
        return job

    def test_closing_waits_for_an_entry_in_flight(self):  # AC-08 (AC-09 de CONT-10)
        locked = threading.Event()

        def post():
            result = self.post()
            locked.set()
            time.sleep(0.3)
            return result

        outcomes = _run_together(post, self.close(locked))
        self.assertEqual(outcomes, [None, None])
        self.assertEqual(JournalEntryModel.objects.count(), 1)

    def test_an_entry_after_a_committed_close_is_rejected(self):  # AC-08
        done = threading.Event()
        done.set()
        _run_together(self.close(done))
        outcomes = _run_together(lambda: self.post())
        self.assertIsInstance(outcomes[0], services.FiscalPeriodClosed)
        self.assertEqual(JournalEntryModel.objects.count(), 0)

    def test_no_entry_is_inserted_after_the_close(self):  # AC-08
        """Carrera libre: tras ambos, o el asiento existe o fue rechazado, y el período queda cerrado."""
        done = threading.Event()
        done.set()
        outcomes = _run_together(lambda: self.post(), self.close(done))
        self.assertTrue(all(o is None or isinstance(o, services.FiscalPeriodClosed) for o in outcomes), outcomes)
        self.assertEqual(DjangoFiscalPeriodRepository(self.company.id).get(self.period.id).status, 'CLOSED')
