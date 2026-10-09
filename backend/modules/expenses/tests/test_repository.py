from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.domain.enums import ExpenseStatus
from modules.expenses.domain.exceptions import ExpenseValidationError
from modules.expenses.domain.expense import Expense
from modules.expenses.domain.repositories import ExpenseFilters
from modules.expenses.infrastructure.django.models import ExpenseCategoryModel, ExpenseModel
from modules.expenses.infrastructure.django.repositories import (
    DjangoExpenseCategoryRepository,
    DjangoExpenseRepository,
)


class RepositoryTestCase(TestCase):
    def setUp(self):
        self.categories = DjangoExpenseCategoryRepository()
        self.expenses = DjangoExpenseRepository()

    def category(self, name='Empaque', active=True):
        category = ExpenseCategory.create(name)
        category.active = active
        return self.categories.save(category)

    def expense(self, category, **overrides):
        values = dict(description='Harina', amount='10.00', category_id=category.id, expense_date=date(2026, 10, 1))
        values.update(overrides)
        return self.expenses.save(Expense.create(**values))


class CategoryRepositoryTests(RepositoryTestCase):
    def test_saves_and_loads_a_category(self):  # AC-01
        saved = self.category('Empaque')
        loaded = self.categories.get(saved.id)
        self.assertEqual((loaded.name, loaded.active), ('Empaque', True))
        self.assertIsNotNone(loaded.created_at)

    def test_updates_an_existing_category(self):  # AC-02
        saved = self.category('Empaque')
        saved.rename('Embalaje')
        saved.deactivate()
        self.categories.save(saved)
        loaded = self.categories.get(saved.id)
        self.assertEqual((loaded.name, loaded.active), ('Embalaje', False))

    def test_name_is_unique_ignoring_case_at_database_level(self):  # AC-01, EDGE-09
        self.category('Empaque')
        with self.assertRaises(ExpenseValidationError) as ctx:
            self.category('EMPAQUE')
        self.assertEqual(list(ctx.exception.errors), ['name'])
        self.assertEqual(ExpenseCategoryModel.objects.count(), 1)

    def test_finds_by_name_ignoring_case_and_excluding_an_id(self):
        saved = self.category('Empaque')
        self.assertEqual(self.categories.find_by_name('empaque').id, saved.id)
        self.assertIsNone(self.categories.find_by_name('empaque', exclude_id=saved.id))
        self.assertIsNone(self.categories.find_by_name('otra'))

    def test_list_filters_by_active_and_search(self):
        self.category('Empaque')
        self.category('Delivery', active=False)
        self.assertEqual([c.name for c in self.categories.list()], ['Delivery', 'Empaque'])
        self.assertEqual([c.name for c in self.categories.list(active=True)], ['Empaque'])
        self.assertEqual([c.name for c in self.categories.list(search='deli')], ['Delivery'])

    def test_get_many_returns_a_mapping(self):
        a, b = self.category('A'), self.category('B')
        self.assertEqual(set(self.categories.get_many([a.id, b.id, uuid4()])), {a.id, b.id})
        self.assertEqual(self.categories.get_many([]), {})

    def test_a_category_with_expenses_cannot_be_deleted(self):  # AC-02, INV-05
        category = self.category()
        self.expense(category)
        with self.assertRaises(ProtectedError):
            ExpenseCategoryModel.objects.get(pk=category.id).delete()


class ExpenseRepositoryTests(RepositoryTestCase):
    def test_saves_and_loads_every_field(self):  # AC-03, AC-09
        category = self.category()
        saved = self.expense(category, payment_method='QR', supplier_name='Molino', notes='n')
        loaded = self.expenses.get(saved.id)
        self.assertEqual(loaded.amount, Decimal('10.00'))
        self.assertEqual((loaded.payment_method.value, loaded.supplier_name, loaded.notes), ('QR', 'Molino', 'n'))
        self.assertEqual((loaded.category_id, loaded.status), (category.id, ExpenseStatus.ACTIVE))

    def test_persists_the_void(self):  # AC-07
        expense = self.expense(self.category())
        expense.void(datetime(2026, 10, 9, tzinfo=timezone.utc))
        self.expenses.save(expense)
        loaded = self.expenses.get(expense.id)
        self.assertEqual(loaded.status, ExpenseStatus.VOIDED)
        self.assertIsNotNone(loaded.voided_at)

    def test_database_rejects_a_non_positive_amount(self):  # INV-01
        category = ExpenseCategoryModel.objects.create(name='X')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExpenseModel.objects.create(category=category, description='d', amount=Decimal('0.00'),
                                        expense_date=date(2026, 10, 1), payment_method='CASH', status='ACTIVE')

    def test_list_filters_by_date_category_and_status(self):  # AC-08
        a, b = self.category('A'), self.category('B')
        first = self.expense(a, expense_date=date(2026, 10, 1))
        second = self.expense(b, expense_date=date(2026, 10, 15))
        voided = self.expense(a, expense_date=date(2026, 10, 20))
        voided.void(datetime(2026, 10, 21, tzinfo=timezone.utc))
        self.expenses.save(voided)

        def ids(**kw):
            return [e.id for e in self.expenses.list(ExpenseFilters(**kw))]

        self.assertEqual(ids(), [second.id, first.id])  # vigentes, más recientes primero
        self.assertEqual(ids(status=None), [voided.id, second.id, first.id])
        self.assertEqual(ids(status=ExpenseStatus.VOIDED), [voided.id])
        self.assertEqual(ids(category_id=b.id), [second.id])
        self.assertEqual(ids(date_from=date(2026, 10, 2), date_to=date(2026, 10, 15)), [second.id])
        self.assertEqual(ids(date_from=date(2026, 10, 15), date_to=date(2026, 10, 15)), [second.id])  # EDGE-02

    def test_total_active_ignores_voided_and_the_status_filter(self):  # AC-08, INV-07
        category = self.category()
        self.expense(category, amount='10.50')
        self.expense(category, amount='4.50')
        gone = self.expense(category, amount='100.00')
        gone.void(datetime(2026, 10, 21, tzinfo=timezone.utc))
        self.expenses.save(gone)
        self.assertEqual(self.expenses.total_active(ExpenseFilters()), Decimal('15.00'))
        self.assertEqual(self.expenses.total_active(ExpenseFilters(status=ExpenseStatus.VOIDED)), Decimal('15.00'))
        self.assertEqual(self.expenses.total_active(ExpenseFilters(date_from=date(2027, 1, 1))), Decimal('0.00'))

    def test_get_for_update_locks_inside_a_transaction(self):  # EDGE-10
        expense = self.expense(self.category())
        with transaction.atomic():
            self.assertEqual(self.expenses.get_for_update(expense.id).id, expense.id)
        self.assertIsNone(self.expenses.get_for_update(uuid4()))
