"""CONT-01 AC-04: la migración 0004 no altera cuentas ni entradas existentes (REV-01)."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [('accounting', '0003_entry_regularization')]
AFTER = [('accounting', '0004_account_kind_classification')]


class AccountKindMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        MigrationExecutor(connection).migrate(targets)
        return MigrationExecutor(connection).loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_existing_accounts_and_entries_keep_their_data_and_are_reversible(self):
        old = self.migrate(BEFORE)
        company, origin = uuid4(), uuid4()
        account = old.get_model('accounting', 'AccountModel').objects.create(
            company_id=company, name='Banco', currency='BOB')
        entry = old.get_model('accounting', 'EntryModel').objects.create(
            company_id=company, account=account, currency='BOB', amount=Decimal('125.50'),
            payment_date=date(2026, 10, 1), payment_method='BANK_TRANSFER', origin_kind='PRODUCT',
            origin_id=origin, origin_document_ref='pedido-1', receipt_number='CB-000001')

        new = self.migrate(AFTER)

        kept_account = new.get_model('accounting', 'AccountModel').objects.get(pk=account.pk)
        self.assertEqual((kept_account.name, kept_account.currency, kept_account.is_active), ('Banco', 'BOB', True))
        self.assertIsNone(kept_account.kind)
        kept = new.get_model('accounting', 'EntryModel').objects.get(pk=entry.pk)
        self.assertEqual((kept.account_id, kept.amount, kept.origin_id, kept.origin_document_ref, kept.receipt_number),
                         (account.pk, Decimal('125.50'), origin, 'pedido-1', 'CB-000001'))

        back = self.migrate(BEFORE)
        self.assertEqual(back.get_model('accounting', 'EntryModel').objects.get(pk=entry.pk).amount, Decimal('125.50'))
