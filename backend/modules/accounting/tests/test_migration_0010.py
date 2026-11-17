"""CONT-02: la migración 0010 es aditiva (tablas de asientos), conserva el libro anterior y se revierte limpia."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [('accounting', '0009_fiscal_period')]
AFTER = [('accounting', '0010_journal_entry')]
JOURNAL_TABLES = {'accounting_journal_entry', 'accounting_journal_line'}


def tables() -> set[str]:
    with connection.cursor() as cursor:
        return set(connection.introspection.table_names(cursor))


class JournalEntryMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        MigrationExecutor(connection).migrate(targets)
        return MigrationExecutor(connection).loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_applies_without_touching_the_legacy_ledger_and_reverts_cleanly(self):
        old = self.migrate(BEFORE)
        self.assertFalse(JOURNAL_TABLES & tables())
        company, origin = uuid4(), uuid4()
        account = old.get_model('accounting', 'AccountModel').objects.create(
            company_id=company, name='Banco', currency='BOB')
        entry = old.get_model('accounting', 'EntryModel').objects.create(
            company_id=company, account=account, currency='BOB', amount=Decimal('80.00'),
            payment_date=date(2026, 10, 1), payment_method='QR', origin_kind='PRODUCT', origin_id=origin)

        new = self.migrate(AFTER)

        self.assertTrue(JOURNAL_TABLES <= tables())
        kept = new.get_model('accounting', 'EntryModel').objects.get(pk=entry.pk)
        self.assertEqual((kept.amount, kept.origin_kind, kept.origin_id), (Decimal('80.00'), 'PRODUCT', origin))
        self.assertEqual(new.get_model('accounting', 'JournalEntryModel').objects.count(), 0)

        back = self.migrate(BEFORE)

        self.assertFalse(JOURNAL_TABLES & tables())
        self.assertEqual(back.get_model('accounting', 'EntryModel').objects.filter(pk=entry.pk).count(), 1)

    def test_database_rejects_zero_total_and_duplicate_origin_per_company(self):
        new = self.migrate(AFTER)
        model = new.get_model('accounting', 'JournalEntryModel')
        company, origin = uuid4(), uuid4()
        period = new.get_model('accounting', 'FiscalPeriodModel').objects.create(
            company_id=company, name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))

        def create(**extra):
            data = dict(company_id=company, accounting_date=date(2026, 10, 1), description='Venta', currency='BOB',
                        total=Decimal('10.00'), period=period, source='AUTOMATIC', origin_kind='SALE',
                        origin_id=origin)
            return model.objects.create(**{**data, **extra})

        with self.assertRaises(IntegrityError), transaction.atomic():  # total > 0
            create(total=Decimal('0.00'), origin_id=uuid4())
        with self.assertRaises(IntegrityError), transaction.atomic():  # tipo de origen sin id de evento
            create(origin_id=None)
        with self.assertRaises(IntegrityError), transaction.atomic():  # fuente desconocida
            create(source='OTHER', origin_id=uuid4())
        create()
        with self.assertRaises(IntegrityError), transaction.atomic():  # un evento, un asiento
            create()
        other = uuid4()  # el mismo origen en otra empresa no choca
        create(company_id=other, period=new.get_model('accounting', 'FiscalPeriodModel').objects.create(
            company_id=other, name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)))
