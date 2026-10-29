from collections.abc import Sequence
from contextlib import contextmanager
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Case, DecimalField, F, QuerySet, Sum, When

from modules.inventory.domain.exceptions import MovementConflict
from modules.inventory.domain.movement import (
    MovementKind,
    MovementSource,
    MovementStatus,
    StockMovement,
)
from modules.inventory.domain.repositories import MovementFilters
from modules.inventory.domain.stock import StockBalanceEntry

from .models import StockMovementModel, WarehouseModel

ZERO = Decimal('0')


def to_entity(model: StockMovementModel, reversed_by_id: UUID | None = None) -> StockMovement:
    source = (MovementSource(model.source_type, model.source_id, model.source_line)
              if model.source_type else None)
    return StockMovement(
        id=model.id, product_id=model.product_id, warehouse_id=model.warehouse_id, kind=MovementKind(model.kind),
        quantity=model.quantity, occurred_at=model.occurred_at, user_id=model.user_id, user_name=model.user_name,
        reference=model.reference, reason=model.reason, source=source, status=MovementStatus(model.status),
        reverses_id=model.reverses_id, created_at=model.created_at, reversed_by_id=reversed_by_id)


class MovementList:
    """Vista perezosa de entidades sobre un queryset (paginable sin cargar todo)."""

    def __init__(self, queryset: QuerySet):
        self._queryset = queryset

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [to_entity(model) for model in self._queryset[index]]
        return to_entity(self._queryset[index])

    def __iter__(self):
        return (to_entity(model) for model in self._queryset)


class BalanceList:
    """Existencias agrupadas por producto y almacén (paginable: cuenta y corta sobre la consulta agrupada)."""

    def __init__(self, rows: QuerySet):
        self._rows = rows

    @staticmethod
    def _entry(row: dict) -> StockBalanceEntry:
        return StockBalanceEntry(
            product_id=row['product_id'], warehouse_id=row['warehouse_id'],
            warehouse_name=row['warehouse__name'], quantity=row['total'])

    def count(self) -> int:
        return self._rows.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self._entry(row) for row in self._rows[index]]
        return self._entry(self._rows[index])

    def __iter__(self):
        return (self._entry(row) for row in self._rows)


def _signed_sum() -> Sum:
    return Sum(Case(When(kind=MovementKind.IN.value, then=F('quantity')), default=-F('quantity'),
                    output_field=DecimalField(max_digits=16, decimal_places=4)))


class DjangoStockMovementRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _movements(self) -> QuerySet:
        return StockMovementModel.objects.filter(company_id=self.company_id)

    @contextmanager
    def locked(self, warehouse_id: UUID):
        with transaction.atomic():
            # Serializa los movimientos del almacén: dos salidas simultáneas no pasan ambas el control de saldo.
            list(WarehouseModel.objects.select_for_update().filter(pk=warehouse_id, company_id=self.company_id))
            yield

    def get(self, movement_id: UUID) -> StockMovement | None:
        model = self._movements().filter(pk=movement_id).first()
        if model is None:
            return None
        counter = self._movements().filter(reverses_id=model.id).values_list('id', flat=True).first()
        return to_entity(model, reversed_by_id=counter)

    def find_by_source(self, movement: StockMovement) -> StockMovement | None:
        if movement.source is None:
            return None
        model = self._movements().filter(
            source_type=movement.source.type, source_id=movement.source.id, source_line=movement.source.line,
            product_id=movement.product_id, warehouse_id=movement.warehouse_id, kind=movement.kind.value).first()
        return to_entity(model) if model else None

    def balance(self, product_id: UUID, warehouse_id: UUID) -> Decimal:
        total = self._movements().filter(product_id=product_id, warehouse_id=warehouse_id).aggregate(
            total=_signed_sum())['total']
        return total or ZERO

    def insert(self, movement: StockMovement) -> StockMovement:
        source = movement.source
        try:
            with transaction.atomic():
                StockMovementModel.objects.create(
                    id=movement.id, company_id=self.company_id, product_id=movement.product_id,
                    warehouse_id=movement.warehouse_id, kind=movement.kind.value, quantity=movement.quantity,
                    occurred_at=movement.occurred_at, user_id=movement.user_id, user_name=movement.user_name,
                    reference=movement.reference, reason=movement.reason,
                    source_type=source.type if source else None, source_id=source.id if source else '',
                    source_line=source.line if source else '', status=movement.status.value,
                    reverses_id=movement.reverses_id)
        except IntegrityError:  # carrera: la restricción única manda
            existing = self.find_by_source(movement)
            if existing is not None:
                return existing
            if movement.reverses_id is not None:
                raise MovementConflict('already_reversed', 'El movimiento ya fue revertido.') from None
            raise
        return self.get(movement.id)

    def mark_reversed(self, movement_id: UUID) -> None:
        self._movements().filter(pk=movement_id).update(status=MovementStatus.REVERSED.value)

    def list(self, filters: MovementFilters) -> MovementList:
        queryset = self._movements().order_by('-occurred_at', '-created_at', 'id')
        if filters.date_from:
            queryset = queryset.filter(occurred_at__date__gte=filters.date_from)
        if filters.date_to:
            queryset = queryset.filter(occurred_at__date__lte=filters.date_to)
        if filters.product_id:
            queryset = queryset.filter(product_id=filters.product_id)
        if filters.warehouse_id:
            queryset = queryset.filter(warehouse_id=filters.warehouse_id)
        if filters.kind:
            queryset = queryset.filter(kind=filters.kind.value)
        if filters.source_type == 'none':
            queryset = queryset.filter(source_type__isnull=True)
        elif filters.source_type:
            queryset = queryset.filter(source_type=filters.source_type)
            if filters.source_id:
                queryset = queryset.filter(source_id=filters.source_id)
        return MovementList(queryset)

    def balances_for(self, warehouse_id: UUID, product_ids) -> dict[UUID, Decimal]:
        rows = (self._movements().filter(warehouse_id=warehouse_id, product_id__in=list(product_ids))
                .values('product_id').annotate(total=_signed_sum()))
        balances = {product_id: ZERO for product_id in product_ids}
        balances.update({row['product_id']: row['total'] or ZERO for row in rows})
        return balances

    def has_history(self, product_id: UUID) -> bool:
        return self._movements().filter(product_id=product_id).exists()

    def has_nonzero_balance(self, warehouse_id: UUID) -> bool:
        rows = (self._movements().filter(warehouse_id=warehouse_id).values('product_id')
                .annotate(total=_signed_sum()).exclude(total=0))
        return rows.exists()

    def find_by_source_id(self, source_type: str, source_id: str) -> Sequence[StockMovement]:
        models = self._movements().filter(source_type=source_type, source_id=source_id).order_by('product_id')
        return [to_entity(model) for model in models]

    def products_with_history(self, warehouse_id: UUID, product_ids) -> set[UUID]:
        return set(self._movements().filter(warehouse_id=warehouse_id, product_id__in=list(product_ids))
                   .values_list('product_id', flat=True))

    def list_balances(self, warehouse_id: UUID | None = None) -> BalanceList:
        queryset = self._movements()
        if warehouse_id is not None:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        rows = (queryset.values('product_id', 'warehouse_id', 'warehouse__name').annotate(total=_signed_sum())
                .order_by('warehouse__name', 'product_id'))
        return BalanceList(rows)
