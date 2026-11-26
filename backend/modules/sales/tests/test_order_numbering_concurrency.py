"""Carrera de numeración (TASK-numeracion-correlativa-pedidos-venta, AC-07/AC-08): PostgreSQL real e hilos."""
import threading
from datetime import date, datetime, timezone

from django.db import transaction
from django.test import TransactionTestCase

from modules.accounting.application.fiscal_periods import CloseFiscalPeriod
from modules.accounting.infrastructure.django.repositories import DjangoFiscalPeriodRepository
from modules.accounts.testing import make_company
from modules.accounting.tests.test_concurrency import _run_together
from modules.sales.application.commands import StartOrderPreparation
from modules.sales.domain.exceptions import OrderRuleViolation
from modules.sales.infrastructure.adapters import OrderNumberingAdapter
from modules.sales.infrastructure.django.models import OrderModel
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository

from .test_order_numbering import make_order, make_period

RACERS = 8


def confirm(company, order):
    """Un hilo que confirma un pedido en su propia transacción, como una petición."""
    def job():
        repository = DjangoOrderRepository(company.id)
        StartOrderPreparation(repository, OrderNumberingAdapter(company.id)).execute(order.id)
    return job


def numbers(company, period_id=None):
    rows = OrderModel.objects.filter(company_id=company.id, number__isnull=False)
    if period_id is not None:
        rows = rows.filter(fiscal_period_id=period_id)
    return sorted(rows.values_list('number', flat=True))


class ConcurrentNumberingTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.period = make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))

    def test_simultaneous_confirmations_in_one_period_get_distinct_consecutive_numbers(self):  # AC-07, INV-01
        orders = [make_order(self.company, date(2026, 3, 1), confirm=False) for _ in range(RACERS)]
        outcomes = _run_together(*[confirm(self.company, order) for order in orders])
        self.assertEqual(outcomes, [None] * RACERS)
        self.assertEqual(numbers(self.company), list(range(1, RACERS + 1)))

    def test_two_periods_and_two_companies_run_independent_series(self):  # AC-01, INV-05
        other = make_company('Empresa B')
        make_period(other, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        second = make_period(self.company, 'Gestión 2027', date(2027, 1, 1), date(2027, 12, 31))
        jobs, total = [], 4
        for _ in range(total):
            jobs.append(confirm(self.company, make_order(self.company, date(2026, 3, 1), confirm=False)))
            jobs.append(confirm(self.company, make_order(self.company, date(2027, 3, 1), confirm=False)))
            jobs.append(confirm(other, make_order(other, date(2026, 3, 1), confirm=False)))
        outcomes = _run_together(*jobs)
        self.assertEqual(outcomes, [None] * len(jobs))
        expected = list(range(1, total + 1))
        self.assertEqual(numbers(self.company, self.period.id), expected)
        self.assertEqual(numbers(self.company, second.id), expected)
        self.assertEqual(numbers(other), expected)

    def test_the_same_order_confirmed_twice_at_once_consumes_one_number(self):  # EDGE-01
        order = make_order(self.company, date(2026, 3, 1), confirm=False)
        outcomes = _run_together(confirm(self.company, order), confirm(self.company, order))
        failed = [o for o in outcomes if o is not None]
        self.assertEqual(len(failed), 1)
        self.assertIsInstance(failed[0], OrderRuleViolation)
        self.assertEqual(failed[0].code, 'invalid_transition')
        self.assertEqual(numbers(self.company), [1])
        self.assertEqual(make_order(self.company, date(2026, 3, 2)).number.number, 2)

    def test_confirming_against_a_close_never_numbers_inside_a_closed_period(self):  # AC-08
        orders = [make_order(self.company, date(2026, 3, 1), confirm=False) for _ in range(4)]
        started = threading.Event()

        def close():
            started.wait(timeout=10)
            CloseFiscalPeriod(DjangoFiscalPeriodRepository(self.company.id)).execute(
                self.period.id, 'Ana', datetime(2026, 11, 25, tzinfo=timezone.utc))

        def first_confirm():
            started.set()
            confirm(self.company, orders[0])()

        jobs = [first_confirm, close] + [confirm(self.company, order) for order in orders[1:]]
        outcomes = _run_together(*jobs)
        unexpected = [o for o in outcomes if o is not None
                      and not (isinstance(o, OrderRuleViolation) and o.code == 'fiscal_period_closed')]
        self.assertEqual(unexpected, [])
        numbered = numbers(self.company)
        self.assertEqual(numbered, list(range(1, len(numbered) + 1)))  # sin huecos entre los numerados antes del cierre
        closed_at = self.period.__class__.objects.get(pk=self.period.id)
        self.assertEqual(closed_at.status, 'CLOSED')
        # después del cierre firme, ya no se numera
        late = make_order(self.company, date(2026, 3, 2), confirm=False)
        with self.assertRaises(OrderRuleViolation) as caught, transaction.atomic():
            confirm(self.company, late)()
        self.assertEqual(caught.exception.code, 'fiscal_period_closed')
