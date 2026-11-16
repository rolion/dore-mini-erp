"""CONT-02: egresos, reversión e idempotencia en el libro (AC-01..AC-07)."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase

from modules.accounting import services
from modules.accounting.domain.account import Account
from modules.accounting.domain.classification import Classification
from modules.accounting.domain.entry import Entry, EntryValidationError
from modules.accounting.infrastructure.django.models import EntryModel
from modules.accounting.infrastructure.django.repositories import (
    DjangoAccountRepository,
    DjangoClassificationRepository,
)
from modules.accounting.tests.test_concurrency import _run_together
from modules.accounts.testing import make_company

DAY = date(2026, 11, 10)


def classification(company, direction='EXPENSE', name='Alquiler', active=True):
    repo = DjangoClassificationRepository(company.id)
    created = Classification.create(name, direction)
    if not active:
        created.deactivate()
    return repo.save(created)


def expense_input(account, classification_id, **overrides):
    data = dict(account_id=account.id, currency=account.currency, amount=Decimal('100.00'), payment_date=DAY,
                method='BANK_TRANSFER', origin_kind='EXPENSE', origin_id=uuid4(), origin_document_ref='gasto-1',
                classification_id=classification_id, recorded_by=3, recorded_by_name='Ana')
    data.update(overrides)
    return services.EntryInput(**data)


class DomainTests(TestCase):
    def test_direction_is_derived_from_the_origin(self):
        for kind, direction in (('PRODUCT', 'INCOME'), ('SERVICE', 'INCOME'), ('EXPENSE', 'EXPENSE'),
                                ('PURCHASE_PAYMENT', 'EXPENSE')):
            entry = Entry.record(account_id=uuid4(), currency='BOB', amount=Decimal('5'), payment_date=DAY,
                                 method='CASH', origin_kind=kind, origin_id=uuid4(), classification_id=uuid4())
            self.assertEqual(entry.direction, direction)
            self.assertEqual(entry.effect, Decimal('5.00') if direction == 'INCOME' else Decimal('-5.00'))

    def test_expense_requires_a_classification_and_a_positive_decimal_amount(self):  # EDGE-01, EDGE-03
        base = dict(account_id=uuid4(), currency='BOB', payment_date=DAY, method='CASH', origin_kind='EXPENSE',
                    origin_id=uuid4(), classification_id=uuid4())
        for field, overrides in (('classification_id', {'classification_id': None}),
                                 ('amount', {'amount': Decimal('0')}), ('amount', {'amount': Decimal('-1')}),
                                 ('amount', {'amount': 10.5}), ('amount', {'amount': Decimal('1.234')})):
            with self.assertRaises(EntryValidationError, msg=overrides) as ctx:
                Entry.record(**{**base, 'amount': Decimal('10'), **overrides})
            self.assertIn(field, ctx.exception.errors)

    def test_reversal_is_the_opposite_linked_movement_and_a_reversal_cannot_be_reversed(self):
        original = Entry.record(account_id=uuid4(), currency='BOB', amount=Decimal('80'), payment_date=DAY,
                                method='CASH', origin_kind='EXPENSE', origin_id=uuid4(), classification_id=uuid4())
        reversal = original.reverse(date(2026, 11, 12))
        self.assertEqual((reversal.direction, reversal.operation, reversal.reverses_id),
                         ('INCOME', 'REVERSAL', original.id))
        self.assertEqual((reversal.account_id, reversal.amount, reversal.currency, reversal.classification_id),
                         (original.account_id, original.amount, original.currency, original.classification_id))
        self.assertEqual(original.effect + reversal.effect, Decimal('0.00'))
        with self.assertRaises(EntryValidationError):
            reversal.reverse(DAY)


class ExpenseEntryTests(TestCase):
    def setUp(self):
        self.company, self.other = make_company('A'), make_company('B')
        self.banco = DjangoAccountRepository(self.company.id).save(Account.create('Banco', 'BOB', 'BANK', Decimal('1000')))
        self.alquiler = classification(self.company)

    def balance(self, account=None):
        account = account or self.banco
        return services.account_balances(self.company.id)[account.id]

    def test_expense_reduces_the_balance_exactly_and_is_stored_with_its_data(self):  # AC-01
        result = services.record_entry(self.company.id, expense_input(self.banco, self.alquiler.id))
        self.assertTrue(result.created)
        self.assertEqual((result.entry.direction, result.entry.operation), ('EXPENSE', 'RECORD'))
        self.assertEqual(self.balance(), Decimal('900.00'))
        row = EntryModel.objects.get(pk=result.entry.id)
        self.assertEqual((row.company_id, row.account_id, row.amount, row.classification_id, row.origin_kind),
                         (self.company.id, self.banco.id, Decimal('100.00'), self.alquiler.id, 'EXPENSE'))

    def test_income_and_expense_net_in_the_balance(self):  # INV-07
        services.record_entry(self.company.id, expense_input(self.banco, self.alquiler.id))
        services.record_entry(self.company.id, services.EntryInput(
            account_id=self.banco.id, currency='BOB', amount=Decimal('40.50'), payment_date=DAY, method='QR',
            origin_kind='PRODUCT', origin_id=uuid4()))
        self.assertEqual(self.balance(), Decimal('940.50'))

    def test_retry_returns_the_same_entry_and_different_data_conflicts(self):  # AC-02
        data = expense_input(self.banco, self.alquiler.id)
        first = services.record_entry(self.company.id, data)
        second = services.record_entry(self.company.id, data)
        self.assertEqual((first.created, second.created, first.entry.id), (True, False, second.entry.id))
        self.assertEqual(self.balance(), Decimal('900.00'))
        other = expense_input(self.banco, self.alquiler.id, origin_id=data.origin_id, amount=Decimal('101.00'))
        with self.assertRaises(services.EntryConflict):
            services.record_entry(self.company.id, other)

    def test_retry_is_not_revalidated_when_the_classification_was_deactivated_later(self):  # AC-02
        data = expense_input(self.banco, self.alquiler.id)
        services.record_entry(self.company.id, data)
        repo = DjangoClassificationRepository(self.company.id)
        deactivated = repo.get(self.alquiler.id)
        deactivated.deactivate()
        repo.save(deactivated)
        self.assertFalse(services.record_entry(self.company.id, data).created)

    def test_invalid_classification_is_rejected_and_nothing_is_stored(self):  # EDGE-03
        foreign = classification(self.other, name='Ajena')
        for bad in (classification(self.company, 'INCOME', 'Ventas').id, classification(self.company, name='Vieja', active=False).id,
                    foreign.id, uuid4()):
            with self.assertRaises(EntryValidationError) as ctx:
                services.record_entry(self.company.id, expense_input(self.banco, bad))
            self.assertIn('classification_id', ctx.exception.errors)
        self.assertEqual(EntryModel.objects.count(), 0)

    def test_expense_currency_must_match_the_account_currency(self):  # EDGE-02
        with self.assertRaises(EntryValidationError) as ctx:
            services.record_entry(self.company.id, expense_input(self.banco, self.alquiler.id, currency='USD'))
        self.assertIn('currency', ctx.exception.errors)
        self.assertEqual(EntryModel.objects.count(), 0)

    def test_account_of_another_company_is_rejected(self):  # AC-05
        foreign = DjangoAccountRepository(self.other.id).save(Account.create('Ajena', 'BOB'))
        with self.assertRaises(EntryValidationError):
            services.record_entry(self.company.id, expense_input(foreign, self.alquiler.id))
        self.assertEqual(EntryModel.objects.count(), 0)

    def test_failure_after_recording_rolls_back_the_origin_operation(self):  # AC-03
        class Boom(Exception):
            pass

        with self.assertRaises(Boom):
            with transaction.atomic():
                services.record_entry(self.company.id, expense_input(self.banco, self.alquiler.id))
                raise Boom
        self.assertEqual(EntryModel.objects.count(), 0)
        self.assertEqual(self.balance(), Decimal('1000.00'))

    def test_reversal_restores_the_balance_once(self):  # AC-04
        data = expense_input(self.banco, self.alquiler.id)
        original = services.record_entry(self.company.id, data)
        first = services.reverse_entry(self.company.id, 'EXPENSE', data.origin_id, date(2026, 11, 12), 5, 'Beto')
        again = services.reverse_entry(self.company.id, 'EXPENSE', data.origin_id, date(2026, 11, 13))
        self.assertEqual((first.created, again.created, first.entry.id), (True, False, again.entry.id))
        self.assertEqual((first.entry.direction, first.entry.operation), ('INCOME', 'REVERSAL'))
        self.assertEqual(self.balance(), Decimal('1000.00'))
        original_row = EntryModel.objects.get(pk=original.entry.id)
        self.assertEqual((original_row.amount, original_row.direction, original_row.operation, original_row.payment_date),
                         (Decimal('100.00'), 'EXPENSE', 'RECORD', DAY))
        self.assertEqual(EntryModel.objects.get(pk=first.entry.id).reverses_id, original.entry.id)
        self.assertEqual(EntryModel.objects.count(), 2)

    def test_reversal_of_an_income_lowers_the_balance_and_works_on_inactive_accounts(self):
        pid = uuid4()
        services.record_entry(self.company.id, services.EntryInput(
            account_id=self.banco.id, currency='BOB', amount=Decimal('60'), payment_date=DAY, method='CASH',
            origin_kind='PRODUCT', origin_id=pid))
        repo = DjangoAccountRepository(self.company.id)
        banco = repo.get(self.banco.id)
        banco.deactivate()
        repo.save(banco)
        services.reverse_entry(self.company.id, 'PRODUCT', pid, DAY)
        self.assertEqual(self.balance(), Decimal('1000.00'))

    def test_reversal_without_original_or_from_another_company_fails(self):  # AC-05, EDGE-04
        data = expense_input(self.banco, self.alquiler.id)
        services.record_entry(self.company.id, data)
        with self.assertRaises(services.EntryNotFound):
            services.reverse_entry(self.other.id, 'EXPENSE', data.origin_id, DAY)
        with self.assertRaises(services.EntryNotFound):
            services.reverse_entry(self.company.id, 'EXPENSE', uuid4(), DAY)
        self.assertEqual(EntryModel.objects.count(), 1)

    def test_balances_ignore_other_companies(self):  # AC-05
        foreign = DjangoAccountRepository(self.other.id).save(Account.create('Ajena', 'BOB'))
        self.assertNotIn(foreign.id, services.account_balances(self.company.id, [foreign.id, self.banco.id]))

    def test_the_contract_requires_the_callers_transaction(self):  # AC-03
        # TestCase envuelve en transacción; se simula la ausencia con la bandera de la conexión.
        original = connection.in_atomic_block
        connection.in_atomic_block = False
        try:
            with self.assertRaises(services.EntryContractError):
                services.record_entry(self.company.id, expense_input(self.banco, self.alquiler.id))
            with self.assertRaises(services.EntryContractError):
                services.reverse_entry(self.company.id, 'EXPENSE', uuid4(), DAY)
        finally:
            connection.in_atomic_block = original


class ConcurrentExpenseTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('A')
        self.banco = DjangoAccountRepository(self.company.id).save(Account.create('Banco', 'BOB', 'BANK', Decimal('500')))
        self.alquiler = classification(self.company)

    def test_simultaneous_requests_for_the_same_expense_create_one_entry(self):  # AC-02
        data = expense_input(self.banco, self.alquiler.id)
        results = []
        outcomes = _run_together(*[lambda: results.append(services.record_entry(self.company.id, data))] * 2)
        self.assertEqual(outcomes, [None, None])
        self.assertEqual(sorted(r.created for r in results), [False, True])
        self.assertEqual(services.account_balances(self.company.id)[self.banco.id], Decimal('400.00'))

    def test_simultaneous_reversals_create_one_reversal(self):  # EDGE-06
        data = expense_input(self.banco, self.alquiler.id)
        with transaction.atomic():
            services.record_entry(self.company.id, data)
        results = []
        outcomes = _run_together(*[lambda: results.append(
            services.reverse_entry(self.company.id, 'EXPENSE', data.origin_id, DAY))] * 2)
        self.assertEqual(outcomes, [None, None])
        self.assertEqual(sorted(r.created for r in results), [False, True])
        self.assertEqual(EntryModel.objects.filter(operation='REVERSAL').count(), 1)
        self.assertEqual(services.account_balances(self.company.id)[self.banco.id], Decimal('500.00'))
