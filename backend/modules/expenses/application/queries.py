from collections.abc import Sequence
from uuid import UUID

from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.domain.exceptions import ExpenseCategoryNotFound, ExpenseNotFound
from modules.expenses.domain.expense import Expense
from modules.expenses.domain.repositories import ExpenseCategoryRepository, ExpenseFilters, ExpenseRepository


class GetExpense:
    def __init__(self, expenses: ExpenseRepository):
        self.expenses = expenses

    def execute(self, expense_id: UUID) -> Expense:
        expense = self.expenses.get(expense_id)
        if expense is None:
            raise ExpenseNotFound(expense_id)
        return expense


class ListExpenses:
    """Las consultas por rango de fechas y por categoría son filtros de esta misma consulta."""

    def __init__(self, expenses: ExpenseRepository):
        self.expenses = expenses

    def execute(self, filters: ExpenseFilters | None = None) -> Sequence[Expense]:
        return self.expenses.list(filters or ExpenseFilters())


class GetExpenseCategory:
    def __init__(self, categories: ExpenseCategoryRepository):
        self.categories = categories

    def execute(self, category_id: UUID) -> ExpenseCategory:
        category = self.categories.get(category_id)
        if category is None:
            raise ExpenseCategoryNotFound(category_id)
        return category


class ListExpenseCategories:
    def __init__(self, categories: ExpenseCategoryRepository):
        self.categories = categories

    def execute(self, active: bool | None = None, search: str | None = None) -> Sequence[ExpenseCategory]:
        return self.categories.list(active=active, search=search)
