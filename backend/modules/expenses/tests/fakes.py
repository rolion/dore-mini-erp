"""Dobles en memoria de los repositorios y del reloj, para probar casos de uso sin base de datos."""
import copy
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.domain.enums import ExpenseStatus
from modules.expenses.domain.expense import Expense
from modules.expenses.domain.repositories import ExpenseFilters

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


class FixedClock:
    def now(self):
        return NOW


class InMemoryExpenseRepository:
    def __init__(self):
        self.expenses: dict[UUID, Expense] = {}

    def get(self, expense_id):
        expense = self.expenses.get(expense_id)
        return copy.deepcopy(expense) if expense else None

    def get_for_update(self, expense_id):
        return self.get(expense_id)

    def save(self, expense):
        self.expenses[expense.id] = copy.deepcopy(expense)
        return copy.deepcopy(expense)

    def _matching(self, filters: ExpenseFilters):
        for expense in self.expenses.values():
            if filters.date_from and expense.expense_date < filters.date_from:
                continue
            if filters.date_to and expense.expense_date > filters.date_to:
                continue
            if filters.category_id and expense.category_id != filters.category_id:
                continue
            yield expense

    def list(self, filters):
        return [e for e in self._matching(filters) if filters.status is None or e.status is filters.status]

    def total_active(self, filters):
        return sum((e.amount for e in self._matching(filters) if e.status is ExpenseStatus.ACTIVE), Decimal('0.00'))


class InMemoryCategoryRepository:
    def __init__(self):
        self.categories: dict[UUID, ExpenseCategory] = {}

    def add(self, name='Empaque', active=True) -> ExpenseCategory:
        category = ExpenseCategory.create(name)
        category.active = active
        return self.save(category)

    def get(self, category_id):
        category = self.categories.get(category_id)
        return copy.deepcopy(category) if category else None

    def get_many(self, category_ids):
        return {i: self.get(i) for i in set(category_ids) if i in self.categories}

    def find_by_name(self, name, exclude_id=None):
        for category in self.categories.values():
            if category.name.lower() == name.lower() and category.id != exclude_id:
                return copy.deepcopy(category)
        return None

    def save(self, category):
        self.categories[category.id] = copy.deepcopy(category)
        return copy.deepcopy(category)

    def list(self, active=None, search=None):
        return [c for c in self.categories.values() if active is None or c.active is active]
