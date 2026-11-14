"""PB-ACC-002: contrato `record_entry` (AC-01, AC-03, AC-04, AC-06; INV-03, INV-04, INV-06, INV-08)."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase

from modules.accounting import services
from modules.accounting.application.use_cases import ConfigureMethod, UpdateAccount
from modules.accounting.domain.account import Account, AccountConflict
from modules.accounting.infrastructure.django.models import EntryModel
from modules.accounting.infrastructure.django.repositories import (
    DjangoAccountRepository,
    DjangoEntryRepository,
    DjangoMethodMappingRepository,
)
from modules.accounts.testing import make_company
from modules.accounting.domain.entry import EntryValidationError


def entry_input(account, **overrides):
    data = dict(account_id=account.id, currency=account.currency, amount=Decimal('100.00'),
                payment_date=date(2026, 11, 1), method='CASH', origin_kind='PRODUCT', origin_id=uuid4(),
                origin_document_ref='pedido-1', recorded_by=7, recorded_by_name='Ana')
    data.update(overrides)
    return services.EntryInput(**data)


class RecordEntryTests(TestCase):
    def setUp(self):
        self.company = make_company('A')
        self.other = make_company('B')
        self.accounts = DjangoAccountRepository(self.company.id)
        self.caja = self.accounts.save(Account.create('Caja', 'BOB'))

    def test_valid_entry_is_stored_with_all_its_fields(self):  # AC-01
        result = services.record_entry(self.company.id, entry_input(self.caja, receipt_number='CB-000001'))
        self.assertTrue(result.created)
        row = EntryModel.objects.get(pk=result.entry_id)
        self.assertEqual((row.company_id, row.account_id, row.currency), (self.company.id, self.caja.id, 'BOB'))
        self.assertEqual((row.amount, row.payment_date, row.payment_method), (Decimal('100.00'), date(2026, 11, 1), 'CASH'))
        self.assertEqual((row.origin_kind, row.origin_document_ref, row.receipt_number), ('PRODUCT', 'pedido-1', 'CB-000001'))
        self.assertEqual((row.recorded_by, row.recorded_by_name), (7, 'Ana'))
        self.assertIsNotNone(row.created_at)

    def test_invalid_data_is_rejected_and_nothing_is_stored(self):  # AC-01, INV-03
        foreign = DjangoAccountRepository(self.other.id).save(Account.create('Caja ajena', 'BOB'))
        usd = self.accounts.save(Account.create('Dólares', 'USD'))
        cases = [
            ('amount', entry_input(self.caja, amount=Decimal('0'))),
            ('amount', entry_input(self.caja, amount=Decimal('-5'))),
            ('account_id', entry_input(foreign)),
            ('account_id', entry_input(self.caja, account_id=uuid4())),
            ('currency', entry_input(usd, currency='BOB')),
        ]
        for field, data in cases:
            with self.assertRaises(EntryValidationError, msg=field) as ctx:
                services.record_entry(self.company.id, data)
            self.assertIn(field, ctx.exception.errors)
        self.assertEqual(EntryModel.objects.count(), 0)

    def test_retry_with_same_data_returns_the_same_entry(self):  # AC-03
        data = entry_input(self.caja)
        first = services.record_entry(self.company.id, data)
        second = services.record_entry(self.company.id, data)
        self.assertEqual((first.created, second.created), (True, False))
        self.assertEqual(first.entry_id, second.entry_id)
        self.assertEqual(EntryModel.objects.count(), 1)

    def test_retry_with_incompatible_data_is_a_conflict(self):  # AC-03
        data = entry_input(self.caja)
        services.record_entry(self.company.id, data)
        banco = self.accounts.save(Account.create('Banco', 'BOB'))
        variants = [
            entry_input(self.caja, origin_id=data.origin_id, amount=Decimal('99.00')),
            entry_input(self.caja, origin_id=data.origin_id, method='QR'),
            entry_input(self.caja, origin_id=data.origin_id, payment_date=date(2026, 11, 2)),
            entry_input(self.caja, origin_id=data.origin_id, receipt_number='CB-000009'),
            entry_input(banco, origin_id=data.origin_id),
        ]
        for variant in variants:
            with self.assertRaises(services.EntryConflict):
                services.record_entry(self.company.id, variant)
        self.assertEqual(EntryModel.objects.get().amount, Decimal('100.00'))

    def test_same_id_from_different_origins_does_not_collide(self):  # AC-02 (parte de unicidad)
        shared = uuid4()
        services.record_entry(self.company.id, entry_input(self.caja, origin_kind='PRODUCT', origin_id=shared))
        result = services.record_entry(self.company.id, entry_input(self.caja, origin_kind='SERVICE', origin_id=shared))
        self.assertTrue(result.created)
        self.assertEqual(EntryModel.objects.count(), 2)

    def test_same_origin_in_different_companies_does_not_collide(self):
        shared = uuid4()
        other_account = DjangoAccountRepository(self.other.id).save(Account.create('Caja', 'BOB'))
        services.record_entry(self.company.id, entry_input(self.caja, origin_id=shared))
        self.assertTrue(services.record_entry(self.other.id, entry_input(other_account, origin_id=shared)).created)

    def test_a_conflict_does_not_break_the_callers_transaction(self):  # AC-04
        data = entry_input(self.caja)
        services.record_entry(self.company.id, data)
        with self.assertRaises(services.EntryConflict):
            services.record_entry(self.company.id, entry_input(self.caja, origin_id=data.origin_id, amount=Decimal('1')))
        self.assertEqual(EntryModel.objects.count(), 1)  # la transacción sigue utilizable

    def test_entry_rolls_back_with_the_callers_transaction(self):  # AC-04
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                services.record_entry(self.company.id, entry_input(self.caja))
                raise RuntimeError('falla posterior del pago')
        self.assertEqual(EntryModel.objects.count(), 0)

    def test_amount_must_be_positive_at_the_database_level(self):  # INV-01 (red de seguridad)
        with self.assertRaises(IntegrityError), transaction.atomic():
            EntryModel.objects.create(company_id=self.company.id, account_id=self.caja.id, currency='BOB',
                                      amount=Decimal('0'), payment_date=date(2026, 11, 1), payment_method='CASH',
                                      origin_kind='PRODUCT', origin_id=uuid4())

    def test_entry_keeps_its_account_after_the_mapping_changes(self):  # AC-06, INV-06
        banco = self.accounts.save(Account.create('Banco', 'BOB'))
        mappings = DjangoMethodMappingRepository(self.company.id)
        ConfigureMethod(self.accounts, mappings).execute('CASH', self.caja.id, True)
        resolved = services.resolve_account(self.company.id, 'CASH')
        result = services.record_entry(self.company.id, entry_input(self.caja, account_id=resolved.account_id))
        ConfigureMethod(self.accounts, mappings).execute('CASH', banco.id, True)
        self.assertEqual(services.resolve_account(self.company.id, 'CASH').account_id, banco.id)
        self.assertEqual(EntryModel.objects.get(pk=result.entry_id).account_id, self.caja.id)

    def test_account_with_entries_cannot_change_currency(self):  # INV-08
        services.record_entry(self.company.id, entry_input(self.caja))
        update = UpdateAccount(self.accounts, DjangoMethodMappingRepository(self.company.id),
                               DjangoEntryRepository(self.company.id))
        with self.assertRaises(AccountConflict) as ctx:
            update.execute(self.caja.id, currency='USD')
        self.assertEqual(ctx.exception.code, 'account_has_entries')
        self.assertEqual(update.execute(self.caja.id, name='Caja chica', currency='BOB').name, 'Caja chica')


class RecordEntryOutsideTransactionTests(TransactionTestCase):
    def test_requires_the_callers_transaction(self):  # AC-04
        company = make_company('A')
        caja = DjangoAccountRepository(company.id).save(Account.create('Caja', 'BOB'))
        with self.assertRaises(services.EntryContractError):
            services.record_entry(company.id, entry_input(caja))
        self.assertEqual(EntryModel.objects.count(), 0)
