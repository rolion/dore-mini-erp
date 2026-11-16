"""CONT-02 AC-06: la migración 0006 conserva las entradas existentes como ingresos originales."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [('accounting', '0005_coverage_settings_opening_balance')]
AFTER = [('accounting', '0006_entry_direction_operation_reversal')]


class EntryDirectionMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        MigrationExecutor(connection).migrate(targets)
        return MigrationExecutor(connection).loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_existing_entries_become_income_records_and_origin_is_unique_per_operation(self):
        old = self.migrate(BEFORE)
        company, origin = uuid4(), uuid4()
        account = old.get_model('accounting', 'AccountModel').objects.create(
            company_id=company, name='Banco', currency='BOB')
        entry = old.get_model('accounting', 'EntryModel').objects.create(
            company_id=company, account=account, currency='BOB', amount=Decimal('125.50'),
            payment_date=date(2026, 10, 1), payment_method='QR', origin_kind='PRODUCT', origin_id=origin)

        new = self.migrate(AFTER)

        model = new.get_model('accounting', 'EntryModel')
        kept = model.objects.get(pk=entry.pk)
        self.assertEqual((kept.direction, kept.operation, kept.reverses_id, kept.classification_id, kept.amount),
                         ('INCOME', 'RECORD', None, None, Decimal('125.50')))
        with self.assertRaises(IntegrityError), transaction.atomic():  # el mismo origen y operación no se repite
            model.objects.create(company_id=company, account_id=account.pk, currency='BOB', amount=Decimal('1'),
                                 payment_date=date(2026, 10, 2), payment_method='QR', origin_kind='PRODUCT',
                                 origin_id=origin)
        model.objects.create(company_id=company, account_id=account.pk, currency='BOB', amount=Decimal('125.50'),
                             payment_date=date(2026, 10, 3), payment_method='QR', origin_kind='PRODUCT',
                             origin_id=origin, direction='EXPENSE', operation='REVERSAL', reverses_id=entry.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():  # una reversión exige su original
            model.objects.create(company_id=company, account_id=account.pk, currency='BOB', amount=Decimal('1'),
                                 payment_date=date(2026, 10, 3), payment_method='QR', origin_kind='SERVICE',
                                 origin_id=uuid4(), operation='REVERSAL')
