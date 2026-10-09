from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from .category import ExpenseCategory
from .enums import ExpenseStatus
from .expense import Expense


@dataclass(frozen=True)
class ExpenseFilters:
    """`status=None` significa todos los estados; por omisión solo los vigentes."""

    date_from: date | None = None
    date_to: date | None = None
    category_id: UUID | None = None
    status: ExpenseStatus | None = ExpenseStatus.ACTIVE


class ExpenseRepository(Protocol):
    def get(self, expense_id: UUID) -> Expense | None: ...

    def get_for_update(self, expense_id: UUID) -> Expense | None:
        """Como `get`, bloqueando la fila hasta el fin de la transacción en curso."""
        ...

    def save(self, expense: Expense) -> Expense: ...

    def list(self, filters: ExpenseFilters) -> Sequence[Expense]: ...

    def total_active(self, filters: ExpenseFilters) -> Decimal:
        """Suma de los gastos vigentes que cumplen fecha y categoría de los filtros (ignora `status`)."""
        ...


class ExpenseCategoryRepository(Protocol):
    def get(self, category_id: UUID) -> ExpenseCategory | None: ...

    def get_many(self, category_ids: Iterable[UUID]) -> dict[UUID, ExpenseCategory]: ...

    def find_by_name(self, name: str, exclude_id: UUID | None = None) -> ExpenseCategory | None:
        """Búsqueda sin distinguir mayúsculas."""
        ...

    def save(self, category: ExpenseCategory) -> ExpenseCategory: ...

    def list(self, active: bool | None = None, search: str | None = None) -> Sequence[ExpenseCategory]: ...
