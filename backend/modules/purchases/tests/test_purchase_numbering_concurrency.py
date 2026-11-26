"""Carrera de numeración de compras (AC-07/AC-08): PostgreSQL real e hilos."""
import threading
import time
from datetime import date, datetime, timezone

from django.db import transaction
from django.test import TransactionTestCase
from django.utils import timezone as dj_timezone

from modules.accounting.application.fiscal_periods import CloseFiscalPeriod
from modules.accounting.infrastructure.django.models import FiscalPeriodModel
from modules.accounting.infrastructure.django.repositories import DjangoFiscalPeriodRepository
from modules.accounting.tests.test_concurrency import _run_together
from modules.accounts.testing import make_company
from modules.purchases.domain.exceptions import PurchaseNumberingRejected
from modules.purchases.infrastructure.adapters import PurchaseNumberingAdapter
from modules.purchases.infrastructure.django.models import PurchaseModel, PurchaseNumberCounterModel
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository

from .test_purchase_numbering import confirm_use_case, make_period, make_purchase

RACERS = 8


def confirm(company, purchase):
    """Un hilo que confirma una compra en su propia transacción, como una petición."""
    def job():
        confirm_use_case(company).execute(purchase.id, dj_timezone.now())
    return job


def numbers(company, period_id=None):
    rows = PurchaseModel.objects.filter(company_id=company.id, number__isnull=False)
    if period_id is not None:
        rows = rows.filter(fiscal_period_id=period_id)
    return sorted(rows.values_list('number', flat=True))


class ConcurrentNumberingTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.period = make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))

    def test_simultaneous_confirmations_in_one_period_get_distinct_consecutive_numbers(self):  # AC-07, INV-01
        purchases = [make_purchase(self.company, date(2026, 3, 1), confirm=False) for _ in range(RACERS)]
        outcomes = _run_together(*[confirm(self.company, purchase) for purchase in purchases])
        self.assertEqual(outcomes, [None] * RACERS)
        self.assertEqual(numbers(self.company), list(range(1, RACERS + 1)))

    def test_two_periods_and_two_companies_run_independent_series(self):  # AC-01, INV-05
        other = make_company('Empresa B')
        make_period(other, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        second = make_period(self.company, 'Gestión 2027', date(2027, 1, 1), date(2027, 12, 31))
        jobs, total = [], 4
        for _ in range(total):
            jobs.append(confirm(self.company, make_purchase(self.company, date(2026, 3, 1), confirm=False)))
            jobs.append(confirm(self.company, make_purchase(self.company, date(2027, 3, 1), confirm=False)))
            jobs.append(confirm(other, make_purchase(other, date(2026, 3, 1), confirm=False)))
        outcomes = _run_together(*jobs)
        self.assertEqual(outcomes, [None] * len(jobs))
        expected = list(range(1, total + 1))
        self.assertEqual(numbers(self.company, self.period.id), expected)
        self.assertEqual(numbers(self.company, second.id), expected)
        self.assertEqual(numbers(other), expected)

    def test_the_same_purchase_confirmed_twice_at_once_consumes_one_number(self):  # EDGE-01
        purchase = make_purchase(self.company, date(2026, 3, 1), confirm=False)
        outcomes = _run_together(confirm(self.company, purchase), confirm(self.company, purchase))
        # La confirmación es idempotente: la segunda espera el bloqueo, ve la compra confirmada y no numera.
        self.assertEqual(outcomes, [None, None])
        self.assertEqual(numbers(self.company), [1])
        self.assertEqual(make_purchase(self.company, date(2026, 3, 2)).number.number, 2)

    def test_a_close_waits_for_the_confirmation_in_flight(self):  # AC-08
        """La confirmación retiene el bloqueo del período; el cierre arranca después y debe esperarla."""
        purchase = make_purchase(self.company, date(2026, 3, 1), confirm=False)
        locked = threading.Event()
        events = []

        def confirming():
            repository = DjangoPurchaseRepository(self.company.id)
            numbering = PurchaseNumberingAdapter(self.company.id)
            confirmed = repository.get(purchase.id, for_update=True)
            confirmed.confirm(dj_timezone.now(), numbering.next_number(confirmed.purchase_date))  # toma el período
            repository.save(confirmed)
            locked.set()
            time.sleep(0.5)  # la confirmación sigue abierta mientras el cierre intenta entrar
            events.append('numbered')

        def closing():
            self.assertTrue(locked.wait(timeout=10))
            CloseFiscalPeriod(DjangoFiscalPeriodRepository(self.company.id)).execute(
                self.period.id, 'Ana', datetime(2026, 11, 25, tzinfo=timezone.utc))
            events.append('closed')

        outcomes = _run_together(confirming, closing)
        self.assertEqual(outcomes, [None, None])
        self.assertEqual(events, ['numbered', 'closed'])
        self.assertEqual(numbers(self.company), [1])  # quedó numerada en el período antes de cerrarse
        self.assertEqual(FiscalPeriodModel.objects.get(pk=self.period.id).status, 'CLOSED')

    def test_after_a_committed_close_confirming_is_rejected_without_numbering(self):  # AC-08, AC-06
        _run_together(lambda: CloseFiscalPeriod(DjangoFiscalPeriodRepository(self.company.id)).execute(
            self.period.id, 'Ana', datetime(2026, 11, 25, tzinfo=timezone.utc)))
        purchases = [make_purchase(self.company, date(2026, 3, 1), confirm=False) for _ in range(3)]
        outcomes = _run_together(*[confirm(self.company, purchase) for purchase in purchases])
        self.assertTrue(all(isinstance(o, PurchaseNumberingRejected) and o.code == 'fiscal_period_closed'
                            for o in outcomes))
        self.assertEqual(numbers(self.company), [])
        self.assertFalse(PurchaseNumberCounterModel.objects.filter(company_id=self.company.id).exists())

    def test_a_late_confirmation_after_a_close_raises_the_period_error(self):  # AC-06
        _run_together(lambda: CloseFiscalPeriod(DjangoFiscalPeriodRepository(self.company.id)).execute(
            self.period.id, 'Ana', datetime(2026, 11, 25, tzinfo=timezone.utc)))
        late = make_purchase(self.company, date(2026, 3, 2), confirm=False)
        with self.assertRaises(PurchaseNumberingRejected) as caught, transaction.atomic():
            confirm(self.company, late)()
        self.assertEqual(caught.exception.code, 'fiscal_period_closed')
