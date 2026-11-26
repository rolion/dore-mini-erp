"""Migraciones de datos 0007 y 0008: numeran el histórico por empresa y período (AC-12)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from modules.accounting.infrastructure.django.models import FiscalPeriodModel
from modules.sales.infrastructure.django.models import OrderModel, OrderNumberCounterModel

BEFORE = [('sales', '0006_order_number_fields')]
AFTER = [('sales', '0007_backfill_order_numbers')]
CANCELLED_AFTER = [('sales', '0008_backfill_cancelled_order_numbers')]
BASE = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def make(company, order_date, status, minutes):
    order = OrderModel.objects.create(
        company_id=company, status=status, sales_channel='WHATSAPP', order_date=order_date, total=Decimal('10.00'),
        payment_status='PENDING')
    OrderModel.objects.filter(pk=order.pk).update(created_at=BASE + timedelta(minutes=minutes))
    return order.pk


class BackfillTests(TransactionTestCase):
    """0007: pedidos confirmados; los cancelados heredados los numera 0008."""

    def migrate(self, targets):
        MigrationExecutor(connection).migrate(targets)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def number(self, pk):
        row = OrderModel.objects.get(pk=pk)
        return (row.fiscal_period_name, row.number)

    def test_backfill_numbers_by_company_and_period_in_creation_order(self):  # AC-12
        self.migrate(BEFORE)
        a, b = uuid4(), uuid4()
        p26 = FiscalPeriodModel.objects.create(
            company_id=a, name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), status='CLOSED')
        FiscalPeriodModel.objects.create(
            company_id=a, name='2027', start_date=date(2027, 1, 1), end_date=date(2027, 12, 31))
        FiscalPeriodModel.objects.create(
            company_id=b, name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        late = make(a, date(2026, 5, 1), 'DELIVERED', 30)
        early = make(a, date(2026, 9, 1), 'IN_PREPARATION', 10)
        next_year = make(a, date(2027, 2, 1), 'READY', 20)
        other_company = make(b, date(2026, 5, 1), 'RETURNED', 5)
        new = make(a, date(2026, 5, 1), 'NEW', 1)
        cancelled = make(a, date(2026, 5, 1), 'CANCELLED', 2)
        outside = make(a, date(2030, 1, 1), 'DELIVERED', 3)

        self.migrate(AFTER)

        self.assertEqual(self.number(early), ('2026', 1))
        self.assertEqual(self.number(late), ('2026', 2))
        self.assertEqual(self.number(next_year), ('2027', 1))
        self.assertEqual(self.number(other_company), ('2026', 1))
        for untouched in (new, cancelled, outside):
            self.assertEqual(self.number(untouched), ('', None))
        self.assertEqual(OrderNumberCounterModel.objects.get(company_id=a, fiscal_period_id=p26.id).last_number, 2)

    def test_running_it_again_does_not_duplicate_or_renumber(self):  # AC-12
        self.migrate(BEFORE)
        company = uuid4()
        FiscalPeriodModel.objects.create(
            company_id=company, name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        first = make(company, date(2026, 5, 1), 'DELIVERED', 1)
        self.migrate(AFTER)
        second = make(company, date(2026, 6, 1), 'DELIVERED', 2)
        self.migrate(BEFORE)
        self.migrate(AFTER)
        self.assertEqual((self.number(first), self.number(second)), (('2026', 1), ('2026', 2)))


class CancelledBackfillTests(TransactionTestCase):
    """0008: los cancelados heredados toman los siguientes números de su período (PLAN v2, AC-12)."""

    def migrate(self, targets):
        MigrationExecutor(connection).migrate(targets)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def number(self, pk):
        row = OrderModel.objects.get(pk=pk)
        return (row.fiscal_period_name, row.number)

    def test_cancelled_orders_continue_each_period_series_and_outside_ones_stay_unnumbered(self):  # AC-12
        self.migrate(BEFORE)
        a, b = uuid4(), uuid4()
        p26 = FiscalPeriodModel.objects.create(
            company_id=a, name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        FiscalPeriodModel.objects.create(
            company_id=b, name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        delivered = make(a, date(2026, 5, 1), 'DELIVERED', 10)
        cancelled_late = make(a, date(2026, 6, 1), 'CANCELLED', 30)
        cancelled_early = make(a, date(2026, 6, 2), 'CANCELLED', 20)
        outside = make(a, date(2030, 1, 1), 'CANCELLED', 40)
        new = make(a, date(2026, 6, 3), 'NEW', 5)
        other_company = make(b, date(2026, 6, 1), 'CANCELLED', 1)

        self.migrate(AFTER)
        self.assertEqual(self.number(cancelled_early), ('', None))  # 0007 no los numera
        self.migrate(CANCELLED_AFTER)

        self.assertEqual(self.number(delivered), ('2026', 1))
        self.assertEqual(self.number(cancelled_early), ('2026', 2))
        self.assertEqual(self.number(cancelled_late), ('2026', 3))
        self.assertEqual(self.number(other_company), ('2026', 1))
        self.assertEqual((self.number(outside), self.number(new)), (('', None), ('', None)))
        self.assertEqual(OrderNumberCounterModel.objects.get(company_id=a, fiscal_period_id=p26.id).last_number, 3)

    def test_running_it_again_does_not_renumber(self):  # AC-12
        self.migrate(BEFORE)
        company = uuid4()
        FiscalPeriodModel.objects.create(
            company_id=company, name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        cancelled = make(company, date(2026, 6, 1), 'CANCELLED', 1)
        self.migrate(CANCELLED_AFTER)
        later = make(company, date(2026, 6, 2), 'CANCELLED', 2)
        self.migrate(AFTER)
        self.migrate(CANCELLED_AFTER)
        self.assertEqual((self.number(cancelled), self.number(later)), (('2026', 1), ('2026', 2)))
