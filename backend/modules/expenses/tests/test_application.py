from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.expenses.application.commands import (
    ActivateExpenseCategory,
    CreateExpense,
    CreateExpenseCategory,
    DeactivateExpenseCategory,
    RenameExpenseCategory,
    UpdateExpense,
    VoidExpense,
)
from modules.expenses.application.queries import GetExpense, ListExpenses
from modules.expenses.domain.enums import ExpenseStatus
from modules.expenses.domain.exceptions import (
    ExpenseCategoryNotFound,
    ExpenseNotFound,
    ExpenseRuleViolation,
    ExpenseValidationError,
)
from modules.expenses.domain.repositories import ExpenseFilters

from .fakes import NOW, FixedClock, InMemoryCategoryRepository, InMemoryExpenseRepository


class ApplicationTestCase(SimpleTestCase):
    def setUp(self):
        self.expenses = InMemoryExpenseRepository()
        self.categories = InMemoryCategoryRepository()

    def create_expense(self, category, **overrides):
        values = dict(description='Harina', amount='50.00', category_id=category.id, expense_date=date(2026, 10, 1))
        values.update(overrides)
        return CreateExpense(self.expenses, self.categories).execute(**values)


class CategoryCommandTests(ApplicationTestCase):
    def test_creates_a_category(self):  # AC-01
        category = CreateExpenseCategory(self.categories).execute(name=' Empaque ')
        self.assertEqual(category.name, 'Empaque')
        self.assertIn(category.id, self.categories.categories)

    def test_rejects_a_duplicate_name_ignoring_case_and_spaces(self):  # AC-01, EDGE-09
        CreateExpenseCategory(self.categories).execute(name='Empaque')
        for name in ('empaque', ' EMPAQUE '):
            with self.assertRaises(ExpenseValidationError) as ctx:
                CreateExpenseCategory(self.categories).execute(name=name)
            self.assertEqual(list(ctx.exception.errors), ['name'])

    def test_requires_a_name(self):  # AC-01
        with self.assertRaises(ExpenseValidationError):
            CreateExpenseCategory(self.categories).execute(name='')

    def test_rename_allows_keeping_the_same_name_but_not_taking_another(self):  # AC-02
        a = self.categories.add('Empaque')
        self.categories.add('Delivery')
        RenameExpenseCategory(self.categories).execute(a.id, name='EMPAQUE')
        with self.assertRaises(ExpenseValidationError):
            RenameExpenseCategory(self.categories).execute(a.id, name='delivery')

    def test_deactivate_and_activate_do_not_touch_expenses(self):  # AC-02
        category = self.categories.add()
        expense = self.create_expense(category)
        DeactivateExpenseCategory(self.categories).execute(category.id)
        self.assertFalse(self.categories.get(category.id).active)
        self.assertEqual(GetExpense(self.expenses).execute(expense.id).category_id, category.id)
        ActivateExpenseCategory(self.categories).execute(category.id)
        self.assertTrue(self.categories.get(category.id).active)

    def test_unknown_category_raises_not_found(self):
        for command in (DeactivateExpenseCategory, ActivateExpenseCategory):
            with self.assertRaises(ExpenseCategoryNotFound):
                command(self.categories).execute(uuid4())


class CreateExpenseTests(ApplicationTestCase):
    def test_creates_and_persists_an_expense(self):  # AC-03
        category = self.categories.add()
        expense = self.create_expense(category)
        self.assertEqual(expense.amount, Decimal('50.00'))
        self.assertEqual(len(self.expenses.expenses), 1)

    def test_rejects_unknown_or_inactive_category(self):  # AC-05, INV-04
        inactive = self.categories.add('Vieja', active=False)
        for category_id in (uuid4(), inactive.id):
            with self.assertRaises(ExpenseValidationError) as ctx:
                CreateExpense(self.expenses, self.categories).execute(
                    description='x', amount='5', category_id=category_id, expense_date=date(2026, 10, 1))
            self.assertEqual(list(ctx.exception.errors), ['category_id'])
        self.assertEqual(self.expenses.expenses, {})

    def test_reports_field_and_category_errors_together(self):  # AC-04
        with self.assertRaises(ExpenseValidationError) as ctx:
            CreateExpense(self.expenses, self.categories).execute(
                description='', amount='0', category_id=uuid4(), expense_date=date(2026, 10, 1))
        self.assertEqual(set(ctx.exception.errors), {'description', 'amount', 'category_id'})

    def test_missing_category_is_a_required_field_error(self):  # AC-04
        with self.assertRaises(ExpenseValidationError) as ctx:
            CreateExpense(self.expenses, self.categories).execute(description='x', amount='5',
                                                                  expense_date=date(2026, 10, 1))
        self.assertEqual(list(ctx.exception.errors), ['category_id'])


class UpdateExpenseTests(ApplicationTestCase):
    def test_updates_amount_and_date(self):  # AC-06
        category = self.categories.add()
        expense = self.create_expense(category)
        updated = UpdateExpense(self.expenses, self.categories).execute(
            expense.id, amount='75.50', expense_date=date(2026, 10, 5))
        self.assertEqual((updated.amount, updated.expense_date), (Decimal('75.50'), date(2026, 10, 5)))

    def test_keeping_an_inactive_category_is_allowed(self):  # AC-05
        category = self.categories.add()
        expense = self.create_expense(category)
        DeactivateExpenseCategory(self.categories).execute(category.id)
        updated = UpdateExpense(self.expenses, self.categories).execute(expense.id, amount='10', category_id=category.id)
        self.assertEqual(updated.category_id, category.id)

    def test_changing_to_an_inactive_or_unknown_category_is_rejected(self):  # AC-05
        category = self.categories.add()
        inactive = self.categories.add('Vieja', active=False)
        expense = self.create_expense(category)
        for target in (inactive.id, uuid4()):
            with self.assertRaises(ExpenseValidationError) as ctx:
                UpdateExpense(self.expenses, self.categories).execute(expense.id, category_id=target)
            self.assertEqual(list(ctx.exception.errors), ['category_id'])
        self.assertEqual(self.expenses.get(expense.id).category_id, category.id)

    def test_changing_to_another_active_category(self):  # AC-06
        a, b = self.categories.add('A'), self.categories.add('B')
        expense = self.create_expense(a)
        updated = UpdateExpense(self.expenses, self.categories).execute(expense.id, category_id=b.id)
        self.assertEqual(updated.category_id, b.id)

    def test_same_validations_as_creation(self):  # AC-06
        expense = self.create_expense(self.categories.add())
        with self.assertRaises(ExpenseValidationError) as ctx:
            UpdateExpense(self.expenses, self.categories).execute(expense.id, amount='-1')
        self.assertEqual(list(ctx.exception.errors), ['amount'])

    def test_unknown_expense(self):
        with self.assertRaises(ExpenseNotFound):
            UpdateExpense(self.expenses, self.categories).execute(uuid4(), amount='5')

    def test_voided_expense_cannot_be_updated(self):  # AC-07
        expense = self.create_expense(self.categories.add())
        VoidExpense(self.expenses, FixedClock()).execute(expense.id)
        with self.assertRaises(ExpenseRuleViolation) as ctx:
            UpdateExpense(self.expenses, self.categories).execute(expense.id, amount='5')
        self.assertEqual(ctx.exception.code, 'expense_voided')


class VoidExpenseTests(ApplicationTestCase):
    def test_voids_and_records_the_time(self):  # AC-07
        expense = self.create_expense(self.categories.add())
        voided = VoidExpense(self.expenses, FixedClock()).execute(expense.id)
        self.assertEqual((voided.status, voided.voided_at), (ExpenseStatus.VOIDED, NOW))

    def test_voiding_twice_fails(self):  # AC-07
        expense = self.create_expense(self.categories.add())
        VoidExpense(self.expenses, FixedClock()).execute(expense.id)
        with self.assertRaises(ExpenseRuleViolation) as ctx:
            VoidExpense(self.expenses, FixedClock()).execute(expense.id)
        self.assertEqual(ctx.exception.code, 'already_voided')

    def test_unknown_expense(self):
        with self.assertRaises(ExpenseNotFound):
            VoidExpense(self.expenses, FixedClock()).execute(uuid4())


class ListExpensesTests(ApplicationTestCase):
    def test_defaults_to_active_expenses_only(self):  # AC-08
        category = self.categories.add()
        keep = self.create_expense(category)
        gone = self.create_expense(category)
        VoidExpense(self.expenses, FixedClock()).execute(gone.id)
        self.assertEqual([e.id for e in ListExpenses(self.expenses).execute()], [keep.id])
        self.assertEqual(len(ListExpenses(self.expenses).execute(ExpenseFilters(status=None))), 2)
