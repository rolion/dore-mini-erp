"""Migración de datos 0011: numera las compras ya confirmadas por empresa y período (AC-12)."""
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from modules.accounting.infrastructure.django.models import FiscalPeriodModel
from modules.purchases.infrastructure.django.models import PurchaseModel, PurchaseNumberCounterModel

BEFORE = [('purchases', '0010_purchase_number_fields')]
AFTER = [('purchases', '0011_backfill_purchase_numbers')]
BASE = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def make(company, purchase_date, status, confirmed_minutes=None, created_minutes=0):
    purchase = PurchaseModel.objects.create(
        company_id=company, supplier_id=uuid4(), purchase_date=purchase_date, status=status,
        confirmed_at=None if confirmed_minutes is None else BASE + timedelta(minutes=confirmed_minutes))
    PurchaseModel.objects.filter(pk=purchase.pk).update(created_at=BASE + timedelta(minutes=created_minutes))
    return purchase.pk


class BackfillTests(TransactionTestCase):
    def migrate(self, targets):
        MigrationExecutor(connection).migrate(targets)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def number(self, pk):
        row = PurchaseModel.objects.get(pk=pk)
        return (row.fiscal_period_name, row.number)

    def test_backfill_numbers_confirmed_ones_by_company_and_period_in_confirmation_order(self):  # AC-12
        self.migrate(BEFORE)
        a, b = uuid4(), uuid4()
        p26 = FiscalPeriodModel.objects.create(
            company_id=a, name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), status='CLOSED')
        FiscalPeriodModel.objects.create(
            company_id=a, name='2027', start_date=date(2027, 1, 1), end_date=date(2027, 12, 31))
        FiscalPeriodModel.objects.create(
            company_id=b, name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        late = make(a, date(2026, 5, 1), 'confirmed', confirmed_minutes=30)
        early = make(a, date(2026, 9, 1), 'confirmed', confirmed_minutes=10)
        cancelled_after_confirming = make(a, date(2026, 6, 1), 'cancelled', confirmed_minutes=20)
        next_year = make(a, date(2027, 2, 1), 'confirmed', confirmed_minutes=15)
        other_company = make(b, date(2026, 5, 1), 'confirmed', confirmed_minutes=5)
        draft = make(a, date(2026, 5, 1), 'draft')
        cancelled_draft = make(a, date(2026, 5, 2), 'cancelled')
        outside = make(a, date(2030, 1, 1), 'confirmed', confirmed_minutes=3)

        self.migrate(AFTER)

        self.assertEqual(self.number(early), ('2026', 1))
        self.assertEqual(self.number(cancelled_after_confirming), ('2026', 2))  # canceladas confirmadas, sí
        self.assertEqual(self.number(late), ('2026', 3))
        self.assertEqual(self.number(next_year), ('2027', 1))
        self.assertEqual(self.number(other_company), ('2026', 1))
        for untouched in (draft, cancelled_draft, outside):
            self.assertEqual(self.number(untouched), ('', None))
        self.assertEqual(PurchaseNumberCounterModel.objects.get(company_id=a, fiscal_period_id=p26.id).last_number, 3)

    def test_running_it_again_does_not_duplicate_or_renumber(self):  # AC-12
        self.migrate(BEFORE)
        company = uuid4()
        FiscalPeriodModel.objects.create(
            company_id=company, name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        first = make(company, date(2026, 5, 1), 'confirmed', confirmed_minutes=1)
        self.migrate(AFTER)
        second = make(company, date(2026, 6, 1), 'confirmed', confirmed_minutes=2)
        self.migrate(BEFORE)
        self.migrate(AFTER)
        self.assertEqual((self.number(first), self.number(second)), (('2026', 1), ('2026', 2)))
