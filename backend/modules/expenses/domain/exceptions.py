from uuid import UUID


class ExpenseValidationError(Exception):
    """Un dato enviado no cumple una regla de dominio; `errors` mapea campo -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class ExpenseRuleViolation(Exception):
    """El gasto está en un estado que no admite la acción; no es atribuible a un campo. `code` es estable."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ExpenseNotFound(Exception):
    def __init__(self, expense_id: UUID):
        super().__init__(f'Gasto {expense_id} no encontrado.')
        self.expense_id = expense_id


class ExpenseCategoryNotFound(Exception):
    def __init__(self, category_id: UUID):
        super().__init__(f'Categoría {category_id} no encontrada.')
        self.category_id = category_id
