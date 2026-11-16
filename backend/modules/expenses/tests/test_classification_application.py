"""CONT-03: asociación categoría -> clasificación e instantánea en el gasto (sin base de datos)."""
from datetime import date
from uuid import uuid4

from django.test import SimpleTestCase

from modules.expenses.application.commands import CreateExpense, SetCategoryClassification, UpdateExpense
from modules.expenses.application.ports import ClassificationInfo
from modules.expenses.domain.exceptions import (
    INVALID,
    NOT_CONFIGURED,
    ExpenseClassificationError,
    ExpenseValidationError,
)

from .fakes import InMemoryCategoryRepository, InMemoryExpenseRepository


class FakeGateway:
    def __init__(self, covered=False):
        self.covered = covered
        self.items: dict = {}

    def add(self, name='Alquiler', direction='EXPENSE', active=True) -> ClassificationInfo:
        info = ClassificationInfo(uuid4(), name, direction, active)
        self.items[info.id] = info
        return info

    def validate_expense_classification(self, classification_id):
        info = self.items.get(classification_id)
        if info is None or not info.active or info.direction != 'EXPENSE':
            raise ExpenseValidationError({'classification_id': ['no válida']})
        return info

    def describe(self, ids):
        return {i: self.items[i] for i in ids if i in self.items}

    def is_covered(self, on):
        return self.covered


class ClassificationTestCase(SimpleTestCase):
    def setUp(self):
        self.expenses = InMemoryExpenseRepository()
        self.categories = InMemoryCategoryRepository()
        self.gateway = FakeGateway()
        self.rent = self.categories.add('Alquiler')

    def associate(self, info, category=None):
        category = category or self.rent
        return SetCategoryClassification(self.categories, self.gateway).execute(category.id, info.id)

    def create(self, category=None):
        category = category or self.rent
        return CreateExpense(self.expenses, self.categories, self.gateway).execute(
            description='Mes', amount='500.00', category_id=category.id, expense_date=date(2026, 11, 15))


class AssociationTests(ClassificationTestCase):
    def test_associates_and_applies_to_the_new_expense(self):  # AC-01
        info = self.gateway.add()
        self.associate(info)
        self.assertEqual(self.create().classification_id, info.id)

    def test_rejects_income_inactive_or_unknown(self):  # AC-02
        for bad in (self.gateway.add('Ventas', direction='INCOME'), self.gateway.add('Vieja', active=False)):
            with self.assertRaises(ExpenseValidationError):
                self.associate(bad)
        with self.assertRaises(ExpenseValidationError):
            SetCategoryClassification(self.categories, self.gateway).execute(self.rent.id, uuid4())
        self.assertIsNone(self.categories.get(self.rent.id).classification_id)

    def test_changing_or_removing_keeps_recorded_expenses(self):  # AC-03
        first, second = self.gateway.add('Alquiler'), self.gateway.add('Local')
        self.associate(first)
        before = self.create()
        self.associate(second)
        SetCategoryClassification(self.categories, self.gateway).execute(self.rent.id, None)
        self.assertEqual(self.expenses.get(before.id).classification_id, first.id)
        self.assertIsNone(self.create().classification_id)


class CoverageTests(ClassificationTestCase):
    def test_covered_without_association_blocks(self):  # AC-06
        self.gateway.covered = True
        with self.assertRaises(ExpenseClassificationError) as caught:
            self.create()
        self.assertEqual(caught.exception.code, NOT_CONFIGURED)
        self.assertEqual(self.expenses.expenses, {})

    def test_covered_with_inactive_classification_blocks(self):  # AC-06
        info = self.gateway.add()
        self.associate(info)
        self.gateway.items[info.id] = ClassificationInfo(info.id, info.name, 'EXPENSE', False)
        self.gateway.covered = True
        with self.assertRaises(ExpenseClassificationError) as caught:
            self.create()
        self.assertEqual(caught.exception.code, INVALID)

    def test_uncovered_saves_without_snapshot_when_not_configured(self):  # AC-06
        self.assertIsNone(self.create().classification_id)

    def test_changing_category_recomputes_the_snapshot(self):  # AC-06
        info = self.gateway.add()
        self.associate(info)
        other = self.categories.add('Otros')
        expense = self.create(other)
        self.assertIsNone(expense.classification_id)
        updated = UpdateExpense(self.expenses, self.categories, self.gateway).execute(
            expense.id, category_id=self.rent.id)
        self.assertEqual(updated.classification_id, info.id)
