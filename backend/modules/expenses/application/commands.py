from uuid import UUID

from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.domain.exceptions import (
    ExpenseCategoryNotFound,
    ExpenseNotFound,
    ExpenseValidationError,
)
from modules.expenses.domain.expense import UNSET, Expense
from modules.expenses.domain.repositories import ExpenseCategoryRepository, ExpenseRepository

from .ports import Clock

DUPLICATE_NAME = 'Ya existe una categoría con ese nombre.'


def _category_errors(categories: ExpenseCategoryRepository, category_id: UUID) -> dict[str, list[str]]:
    """Regla de aplicación: una categoría nueva para un gasto debe existir y estar activa."""
    category = categories.get(category_id)
    if category is None:
        return {'category_id': ['La categoría no existe.']}
    if not category.active:
        return {'category_id': ['La categoría está inactiva y no puede usarse en un gasto.']}
    return {}


class CreateExpense:
    def __init__(self, expenses: ExpenseRepository, categories: ExpenseCategoryRepository):
        self.expenses = expenses
        self.categories = categories

    def execute(self, description: object = None, amount: object = None, category_id: object = None,
                expense_date: object = None, payment_method: object = None, supplier_name: object = '',
                notes: object = '') -> Expense:
        errors: dict[str, list[str]] = {}
        expense = None
        try:
            expense = Expense.create(description=description, amount=amount, category_id=category_id,
                                     expense_date=expense_date, payment_method=payment_method,
                                     supplier_name=supplier_name, notes=notes)
        except ExpenseValidationError as exc:
            errors.update(exc.errors)
        if isinstance(category_id, UUID) and 'category_id' not in errors:
            errors.update(_category_errors(self.categories, category_id))
        if errors:
            raise ExpenseValidationError(errors)
        return self.expenses.save(expense)


class UpdateExpense:
    """Edición parcial. Conservar la categoría actual es válido aunque esté inactiva; cambiarla exige una activa."""

    def __init__(self, expenses: ExpenseRepository, categories: ExpenseCategoryRepository):
        self.expenses = expenses
        self.categories = categories

    def execute(self, expense_id: UUID, description: object = UNSET, amount: object = UNSET,
                category_id: object = UNSET, expense_date: object = UNSET, payment_method: object = UNSET,
                supplier_name: object = UNSET, notes: object = UNSET) -> Expense:
        expense = self.expenses.get_for_update(expense_id)
        if expense is None:
            raise ExpenseNotFound(expense_id)
        expense.ensure_editable()
        original_category = expense.category_id
        errors: dict[str, list[str]] = {}
        try:
            expense.update(description=description, amount=amount, category_id=category_id,
                           expense_date=expense_date, payment_method=payment_method,
                           supplier_name=supplier_name, notes=notes)
        except ExpenseValidationError as exc:
            errors.update(exc.errors)
        changes_category = isinstance(category_id, UUID) and category_id != original_category
        if changes_category and 'category_id' not in errors:
            errors.update(_category_errors(self.categories, category_id))
        if errors:
            raise ExpenseValidationError(errors)
        return self.expenses.save(expense)


class VoidExpense:
    def __init__(self, expenses: ExpenseRepository, clock: Clock):
        self.expenses = expenses
        self.clock = clock

    def execute(self, expense_id: UUID) -> Expense:
        expense = self.expenses.get_for_update(expense_id)
        if expense is None:
            raise ExpenseNotFound(expense_id)
        expense.void(self.clock.now())
        return self.expenses.save(expense)


def _check_unique_name(categories: ExpenseCategoryRepository, name: str, exclude_id: UUID | None = None) -> None:
    if categories.find_by_name(name, exclude_id=exclude_id) is not None:
        raise ExpenseValidationError({'name': [DUPLICATE_NAME]})


class CreateExpenseCategory:
    def __init__(self, categories: ExpenseCategoryRepository):
        self.categories = categories

    def execute(self, name: object = None) -> ExpenseCategory:
        category = ExpenseCategory.create(name)
        _check_unique_name(self.categories, category.name)
        return self.categories.save(category)


def _load_category(categories: ExpenseCategoryRepository, category_id: UUID) -> ExpenseCategory:
    category = categories.get(category_id)
    if category is None:
        raise ExpenseCategoryNotFound(category_id)
    return category


class RenameExpenseCategory:
    def __init__(self, categories: ExpenseCategoryRepository):
        self.categories = categories

    def execute(self, category_id: UUID, name: object = None) -> ExpenseCategory:
        category = _load_category(self.categories, category_id)
        category.rename(name)
        _check_unique_name(self.categories, category.name, exclude_id=category.id)
        return self.categories.save(category)


class ActivateExpenseCategory:
    def __init__(self, categories: ExpenseCategoryRepository):
        self.categories = categories

    def execute(self, category_id: UUID) -> ExpenseCategory:
        category = _load_category(self.categories, category_id)
        category.activate()
        return self.categories.save(category)


class DeactivateExpenseCategory:
    def __init__(self, categories: ExpenseCategoryRepository):
        self.categories = categories

    def execute(self, category_id: UUID) -> ExpenseCategory:
        category = _load_category(self.categories, category_id)
        category.deactivate()
        return self.categories.save(category)
