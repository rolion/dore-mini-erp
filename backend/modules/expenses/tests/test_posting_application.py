"""GAS-01: casos de uso de gastos con el puerto de asiento (sin base de datos)."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.expenses.application.commands import CreateExpense, UpdateExpense, VoidExpense
from modules.expenses.application.ports import PostedAccounts
from modules.expenses.domain.exceptions import (
    ExpensePostingError,
    ExpenseRuleViolation,
    ExpenseValidationError,
)

from .fakes import FixedClock, InMemoryCategoryRepository, InMemoryExpenseRepository

DAY = date(2026, 10, 9)


class FakePosting:
    def __init__(self, covered=True):
        self.covered, self.posted, self.reversed, self.fail = covered, [], [], None
        self.bad_accounts: set = set()

    def is_covered(self, on):
        return self.covered

    def validate_accounts(self, expense_account_id, payment_account_id):
        errors = {f: ['no válida'] for f, a in (('expense_account_id', expense_account_id),
                                                 ('payment_account_id', payment_account_id)) if a in self.bad_accounts}
        if errors:
            raise ExpenseValidationError(errors)

    def post(self, expense, category_name, expense_account_id, payment_account_id):
        if self.fail:
            raise self.fail
        accounts = PostedAccounts(expense_account_id or uuid4(), payment_account_id or uuid4())
        self.posted.append((expense.id, expense.amount, accounts))
        return accounts

    def reverse(self, expense_id):
        if self.fail:
            raise self.fail
        self.reversed.append(expense_id)


class Base(SimpleTestCase):
    def setUp(self):
        self.expenses, self.categories, self.posting = InMemoryExpenseRepository(), InMemoryCategoryRepository(), FakePosting()
        self.category = self.categories.add('Alquiler')

    def create_case(self):
        return CreateExpense(self.expenses, self.categories, posting=self.posting)

    def create(self, **extra):
        data = {'description': 'Alquiler', 'amount': '500.00', 'category_id': self.category.id, 'expense_date': DAY,
                'payment_method': 'BANK_TRANSFER', **extra}
        return self.create_case().execute(**data)


class CreateTests(Base):
    def test_covered_expense_is_posted_with_the_returned_accounts(self):
        expense = self.create()
        self.assertTrue(expense.is_posted)
        self.assertEqual(self.posting.posted[0][1], Decimal('500.00'))
        self.assertEqual(self.expenses.get(expense.id).expense_account_id, expense.expense_account_id)

    def test_uncovered_expense_is_saved_without_accounts(self):
        self.posting.covered = False
        self.posting.bad_accounts = {uuid4()}
        expense = self.create(expense_account_id=next(iter(self.posting.bad_accounts)))
        self.assertFalse(expense.is_posted)
        self.assertEqual(self.posting.posted, [])

    def test_invalid_accounts_are_field_errors(self):
        bad = uuid4()
        self.posting.bad_accounts = {bad}
        with self.assertRaises(ExpenseValidationError) as caught:
            self.create(expense_account_id=bad)
        self.assertEqual(list(caught.exception.errors), ['expense_account_id'])
        self.assertEqual(self.expenses.expenses, {})

    def test_a_posting_failure_propagates(self):
        self.posting.fail = ExpensePostingError('fiscal_period_closed', 'cerrado')
        with self.assertRaises(ExpensePostingError):
            self.create()

    def test_same_key_and_data_returns_the_existing_expense(self):
        key = uuid4()
        first = self.create(idempotency_key=key)
        case = self.create_case()
        again = case.execute(description='Alquiler', amount='500.00', category_id=self.category.id,
                             expense_date=DAY, payment_method='BANK_TRANSFER', idempotency_key=key)
        self.assertTrue(case.replayed)
        self.assertEqual((again.id, len(self.expenses.expenses), len(self.posting.posted)), (first.id, 1, 1))

    def test_same_key_with_other_data_or_other_chosen_account_is_a_conflict(self):
        key = uuid4()
        self.create(idempotency_key=key)
        for change in ({'amount': '501.00'}, {'expense_account_id': uuid4()}):
            with self.subTest(change=change), self.assertRaises(ExpenseRuleViolation) as caught:
                self.create(idempotency_key=key, **change)
            self.assertEqual(caught.exception.code, 'idempotency_key_reused')

    def test_losing_the_race_returns_the_winner(self):
        key = uuid4()
        winner = self.create(idempotency_key=key)

        class Racing(InMemoryExpenseRepository):
            """El primer `find_by_key` no ve al ganador (la otra transacción aún no confirmaba); luego sí."""

            def __init__(self, base):
                super().__init__()
                self.expenses, self.calls = base.expenses, 0

            def find_by_key(self, idempotency_key):
                self.calls += 1
                return None if self.calls == 1 else super().find_by_key(idempotency_key)

        case = CreateExpense(Racing(self.expenses), self.categories, posting=self.posting)
        result = case.execute(description='Alquiler', amount='500.00', category_id=self.category.id,
                              expense_date=DAY, payment_method='BANK_TRANSFER', idempotency_key=key)
        self.assertEqual((result.id, case.replayed, len(self.posting.posted)), (winner.id, True, 1))


class LockAndVoidTests(Base):
    def test_locked_fields_of_a_posted_expense_cannot_change(self):
        expense = self.create()
        update = UpdateExpense(self.expenses, self.categories)
        for change in ({'amount': '1.00'}, {'expense_date': date(2026, 10, 10)}, {'payment_method': 'CASH'},
                       {'category_id': self.categories.add('Otra').id}):
            with self.subTest(change=change), self.assertRaises(ExpenseRuleViolation) as caught:
                update.execute(expense.id, **change)
            self.assertEqual(caught.exception.code, 'expense_posted_locked')
        updated = update.execute(expense.id, description='Nueva', notes='n', amount='500.00')
        self.assertEqual((updated.description, updated.notes), ('Nueva', 'n'))

    def test_an_unposted_expense_is_still_fully_editable(self):
        self.posting.covered = False
        expense = self.create()
        self.assertEqual(UpdateExpense(self.expenses, self.categories).execute(expense.id, amount='9.00').amount,
                         Decimal('9.00'))

    def test_void_reverses_only_posted_expenses_and_a_failure_keeps_it_active(self):
        posted = self.create()
        void = VoidExpense(self.expenses, FixedClock(), self.posting)
        self.posting.fail = ExpensePostingError('fiscal_period_closed', 'cerrado')
        with self.assertRaises(ExpensePostingError):
            void.execute(posted.id)
        self.assertFalse(self.expenses.get(posted.id).voided)
        self.posting.fail = None
        self.assertTrue(void.execute(posted.id).voided)
        self.assertEqual(self.posting.reversed, [posted.id])
        self.posting.covered = False
        plain = self.create()
        void.execute(plain.id)
        self.assertEqual(self.posting.reversed, [posted.id])
