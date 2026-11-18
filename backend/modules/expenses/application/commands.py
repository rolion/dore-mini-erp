from uuid import UUID

from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.domain.exceptions import (
    ExpenseCategoryNotFound,
    ExpenseDuplicateKey,
    ExpenseNotFound,
    ExpenseRuleViolation,
    ExpenseValidationError,
)
from modules.expenses.domain.expense import UNSET, Expense
from modules.expenses.domain.repositories import ExpenseCategoryRepository, ExpenseRepository

from .ports import ClassificationGateway, Clock, ExpensePostingGateway

DUPLICATE_NAME = 'Ya existe una categoría con ese nombre.'


def _category_errors(categories: ExpenseCategoryRepository, category_id: UUID) -> dict[str, list[str]]:
    """Regla de aplicación: una categoría nueva para un gasto debe existir y estar activa."""
    category = categories.get(category_id)
    if category is None:
        return {'category_id': ['La categoría no existe.']}
    if not category.active:
        return {'category_id': ['La categoría está inactiva y no puede usarse en un gasto.']}
    return {}


def resolve_classification(category: ExpenseCategory, classifications: ClassificationGateway | None) -> UUID | None:
    """Clasificación a guardar en el gasto (instantánea informativa de la asociación vigente de su categoría).

    Ya no se exige: la contabilización usa las cuentas del gasto (GAS-01). Si la asociación no sirve, queda vacía.
    """
    if classifications is None or category.classification_id is None:
        return None
    info = classifications.describe([category.classification_id]).get(category.classification_id)
    if info is None or not info.active or info.direction != 'EXPENSE':
        return None
    return category.classification_id


class CreateExpense:
    """Registra un gasto pagado. Con Contabilidad cubriendo la fecha lo contabiliza en la misma transacción.

    Idempotente por `idempotency_key`: un reintento con los mismos datos devuelve el gasto existente
    (`self.replayed`); con otros datos lanza `ExpenseRuleViolation('idempotency_key_reused')`.
    """

    def __init__(self, expenses: ExpenseRepository, categories: ExpenseCategoryRepository,
                 classifications: ClassificationGateway | None = None, posting: ExpensePostingGateway | None = None):
        self.expenses = expenses
        self.categories = categories
        self.classifications = classifications
        self.posting = posting
        self.replayed = False

    def _replay(self, existing: Expense, submitted: Expense, expense_account_id, payment_account_id) -> Expense:
        if not existing.same_submission(submitted, expense_account_id, payment_account_id):
            raise ExpenseRuleViolation('idempotency_key_reused', 'La clave de la operación ya se usó con otros datos.')
        self.replayed = True
        return existing

    def execute(self, description: object = None, amount: object = None, category_id: object = None,
                expense_date: object = None, payment_method: object = None, supplier_name: object = '',
                notes: object = '', expense_account_id: UUID | None = None, payment_account_id: UUID | None = None,
                idempotency_key: UUID | None = None) -> Expense:
        self.replayed = False
        errors: dict[str, list[str]] = {}
        expense = None
        try:
            expense = Expense.create(description=description, amount=amount, category_id=category_id,
                                     expense_date=expense_date, payment_method=payment_method,
                                     supplier_name=supplier_name, notes=notes, idempotency_key=idempotency_key)
        except ExpenseValidationError as exc:
            errors.update(exc.errors)
        if expense is not None and idempotency_key is not None:
            existing = self.expenses.find_by_key(idempotency_key)
            if existing is not None:
                return self._replay(existing, expense, expense_account_id, payment_account_id)
        if isinstance(category_id, UUID) and 'category_id' not in errors:
            errors.update(_category_errors(self.categories, category_id))
        covered = (expense is not None and self.posting is not None and self.posting.is_covered(expense.expense_date))
        if covered:
            try:
                self.posting.validate_accounts(expense_account_id, payment_account_id)
            except ExpenseValidationError as exc:
                errors.update(exc.errors)
        if errors:
            raise ExpenseValidationError(errors)
        category = self.categories.get(expense.category_id)
        expense.assign_classification(resolve_classification(category, self.classifications))
        try:
            saved = self.expenses.save(expense)
        except ExpenseDuplicateKey:  # carrera: otra petición con la misma clave ganó
            return self._replay(self.expenses.find_by_key(idempotency_key), expense, expense_account_id,
                                payment_account_id)
        if covered:
            accounts = self.posting.post(saved, category.name, expense_account_id, payment_account_id)
            if accounts is not None:
                saved.assign_posting(accounts.expense_account_id, accounts.payment_account_id)
                saved = self.expenses.save(saved)
        return saved


class UpdateExpense:
    """Edición parcial. Conservar la categoría actual es válido aunque esté inactiva; cambiarla exige una activa."""

    def __init__(self, expenses: ExpenseRepository, categories: ExpenseCategoryRepository,
                 classifications: ClassificationGateway | None = None):
        self.expenses = expenses
        self.categories = categories
        self.classifications = classifications

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
        if changes_category:
            category = self.categories.get(expense.category_id)
            expense.assign_classification(resolve_classification(category, self.classifications))
        return self.expenses.save(expense)


class VoidExpense:
    """Anula el gasto; si está contabilizado, revierte su asiento en la misma transacción (si falla, no se anula)."""

    def __init__(self, expenses: ExpenseRepository, clock: Clock, posting: ExpensePostingGateway | None = None):
        self.expenses = expenses
        self.clock = clock
        self.posting = posting

    def execute(self, expense_id: UUID, actor_id: int | None = None, actor_name: str = '') -> Expense:
        expense = self.expenses.get_for_update(expense_id)
        if expense is None:
            raise ExpenseNotFound(expense_id)
        expense.void(self.clock.now())
        if expense.is_posted and self.posting is not None:
            self.posting.reverse(expense.id, actor_id, actor_name)
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


class SetCategoryClassification:
    """Asocia una clasificación de egreso activa de la empresa a la categoría, o la quita con `None`.

    Solo afecta a los gastos nuevos: los registrados conservan la clasificación con que se crearon.
    """

    def __init__(self, categories: ExpenseCategoryRepository, classifications: ClassificationGateway):
        self.categories = categories
        self.classifications = classifications

    def execute(self, category_id: UUID, classification_id: UUID | None = None) -> ExpenseCategory:
        category = _load_category(self.categories, category_id)
        if classification_id is not None:
            self.classifications.validate_expense_classification(classification_id)
        category.set_classification(classification_id)
        return self.categories.save(category)
