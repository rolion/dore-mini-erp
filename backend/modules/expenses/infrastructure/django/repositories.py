from collections.abc import Callable, Iterable
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet, Sum

from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.domain.enums import ExpenseStatus
from modules.expenses.domain.exceptions import ExpenseValidationError
from modules.expenses.domain.expense import Expense
from modules.expenses.domain.repositories import ExpenseFilters

from .mappers import category_to_entity, category_to_values, expense_to_entity, expense_to_values
from .models import ExpenseCategoryModel, ExpenseModel

DUPLICATE_NAME = 'Ya existe una categoría con ese nombre.'


class LazyList:
    """Vista perezosa de entidades sobre un queryset: permite paginar sin cargar todas las filas."""

    def __init__(self, queryset: QuerySet, to_entity: Callable):
        self._queryset = queryset
        self._to_entity = to_entity

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self._to_entity(model) for model in self._queryset[index]]
        return self._to_entity(self._queryset[index])

    def __iter__(self):
        return (self._to_entity(model) for model in self._queryset)


def _filtered(filters: ExpenseFilters, include_status: bool) -> QuerySet:
    queryset = ExpenseModel.objects.all()
    if filters.date_from is not None:
        queryset = queryset.filter(expense_date__gte=filters.date_from)
    if filters.date_to is not None:
        queryset = queryset.filter(expense_date__lte=filters.date_to)
    if filters.category_id is not None:
        queryset = queryset.filter(category_id=filters.category_id)
    if include_status and filters.status is not None:
        queryset = queryset.filter(status=filters.status.value)
    return queryset


class DjangoExpenseRepository:
    def get(self, expense_id: UUID) -> Expense | None:
        model = ExpenseModel.objects.filter(pk=expense_id).first()
        return expense_to_entity(model) if model else None

    def get_for_update(self, expense_id: UUID) -> Expense | None:
        """Bloquea la fila (exige una transacción abierta) y la lee ya con el bloqueo."""
        model = ExpenseModel.objects.select_for_update().filter(pk=expense_id).first()
        return expense_to_entity(model) if model else None

    def save(self, expense: Expense) -> Expense:
        model, _ = ExpenseModel.objects.update_or_create(id=expense.id, defaults=expense_to_values(expense))
        return expense_to_entity(model)

    def list(self, filters: ExpenseFilters) -> LazyList:
        return LazyList(_filtered(filters, include_status=True), expense_to_entity)

    def total_active(self, filters: ExpenseFilters) -> Decimal:
        queryset = _filtered(filters, include_status=False).filter(status=ExpenseStatus.ACTIVE.value)
        return queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')


class DjangoExpenseCategoryRepository:
    def get(self, category_id: UUID) -> ExpenseCategory | None:
        model = ExpenseCategoryModel.objects.filter(pk=category_id).first()
        return category_to_entity(model) if model else None

    def get_many(self, category_ids: Iterable[UUID]) -> dict[UUID, ExpenseCategory]:
        ids = set(category_ids)
        if not ids:
            return {}
        return {m.id: category_to_entity(m) for m in ExpenseCategoryModel.objects.filter(pk__in=ids)}

    def find_by_name(self, name: str, exclude_id: UUID | None = None) -> ExpenseCategory | None:
        queryset = ExpenseCategoryModel.objects.filter(name__iexact=name.strip())
        if exclude_id is not None:
            queryset = queryset.exclude(pk=exclude_id)
        model = queryset.first()
        return category_to_entity(model) if model else None

    def save(self, category: ExpenseCategory) -> ExpenseCategory:
        try:
            with transaction.atomic():
                model, _ = ExpenseCategoryModel.objects.update_or_create(
                    id=category.id, defaults=category_to_values(category))
        except IntegrityError:
            # Carrera entre dos altas con el mismo nombre: la restricción única de la BD es la última barrera.
            raise ExpenseValidationError({'name': [DUPLICATE_NAME]}) from None
        return category_to_entity(model)

    def list(self, active: bool | None = None, search: str | None = None) -> LazyList:
        queryset = ExpenseCategoryModel.objects.order_by('name', 'id')
        if active is not None:
            queryset = queryset.filter(active=active)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return LazyList(queryset, category_to_entity)
