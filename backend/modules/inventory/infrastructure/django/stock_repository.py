from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from modules.inventory.domain.exceptions import OpeningConflict
from modules.inventory.domain.stock import (
    OPENING,
    OpeningLine,
    RegisteredOpening,
    StockBalanceEntry,
    StockMovementEntry,
    StockOpening,
)
from modules.inventory.domain.warehouse import Warehouse

from .models import StockBalanceModel, StockMovementModel, WarehouseModel
from .repositories import to_entity as warehouse_to_entity


class _LazyList:
    """Vista perezosa de entidades sobre un queryset (paginable sin cargar todo)."""

    def __init__(self, queryset: QuerySet, convert):
        self._queryset = queryset
        self._convert = convert

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self._convert(model) for model in self._queryset[index]]
        return self._convert(self._queryset[index])

    def __iter__(self):
        return (self._convert(model) for model in self._queryset)


def _balance_to_entry(model: StockBalanceModel) -> StockBalanceEntry:
    return StockBalanceEntry(
        product_id=model.product_id, warehouse_id=model.warehouse_id, warehouse_name=model.warehouse.name,
        quantity=model.quantity)


def _movement_to_entry(model: StockMovementModel) -> StockMovementEntry:
    return StockMovementEntry(
        id=model.id, product_id=model.product_id, warehouse_id=model.warehouse_id,
        movement_type=model.movement_type, quantity=model.quantity, movement_date=model.movement_date,
        reference=model.reference, created_at=model.created_at)


class DjangoStockRepository:
    """Movimientos y saldos de una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    @contextmanager
    def atomic(self) -> Iterator[None]:
        with transaction.atomic():
            yield

    def lock_warehouse(self, warehouse_id: UUID) -> Warehouse | None:
        """Bloquea la fila del almacén hasta el fin de la transacción: serializa las aperturas del almacén."""
        model = WarehouseModel.objects.select_for_update().filter(
            company_id=self.company_id, pk=warehouse_id).first()
        return warehouse_to_entity(model) if model else None

    def find_opening(self, opening_id: UUID) -> RegisteredOpening | None:
        rows = list(StockMovementModel.objects.filter(
            company_id=self.company_id, opening_id=opening_id).order_by('product_id'))
        if not rows:
            return None
        first = rows[0]
        opening = StockOpening(
            opening_id=opening_id, warehouse_id=first.warehouse_id, movement_date=first.movement_date,
            reference=first.reference, lines=tuple(OpeningLine(row.product_id, row.quantity) for row in rows))
        return RegisteredOpening(opening, {row.product_id: row.id for row in rows})

    def products_with_history(self, warehouse_id: UUID, product_ids: list[UUID]) -> set[UUID]:
        return set(StockMovementModel.objects.filter(
            company_id=self.company_id, warehouse_id=warehouse_id, product_id__in=product_ids,
        ).values_list('product_id', flat=True))

    def save_opening(self, opening: StockOpening, created_by_id: int | None) -> None:
        """Crea un movimiento y su saldo por línea. Una violación de unicidad se informa como `OpeningConflict`."""
        try:
            with transaction.atomic():
                for line in opening.lines:
                    StockMovementModel.objects.create(
                        company_id=self.company_id, warehouse_id=opening.warehouse_id, product_id=line.product_id,
                        movement_type=OPENING, quantity=line.quantity, movement_date=opening.movement_date,
                        reference=opening.reference, opening_id=opening.opening_id, created_by_id=created_by_id)
                    StockBalanceModel.objects.create(
                        company_id=self.company_id, warehouse_id=opening.warehouse_id,
                        product_id=line.product_id, quantity=line.quantity)
        except IntegrityError:
            raise OpeningConflict() from None

    def list_balances(self, warehouse_id: UUID | None = None) -> _LazyList:
        queryset = StockBalanceModel.objects.filter(company_id=self.company_id).select_related('warehouse')
        if warehouse_id is not None:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        return _LazyList(queryset, _balance_to_entry)

    def get_balance(self, warehouse_id: UUID, product_id: UUID) -> StockBalanceEntry | None:
        model = StockBalanceModel.objects.filter(
            company_id=self.company_id, warehouse_id=warehouse_id, product_id=product_id,
        ).select_related('warehouse').first()
        return _balance_to_entry(model) if model else None

    def list_movements(self, warehouse_id: UUID, product_id: UUID) -> _LazyList:
        queryset = StockMovementModel.objects.filter(
            company_id=self.company_id, warehouse_id=warehouse_id, product_id=product_id)
        return _LazyList(queryset, _movement_to_entry)


def has_movements(company_id: UUID, product_id: UUID) -> bool:
    """Proveedor de `shared.stock_history`: el producto de la empresa tiene algún movimiento."""
    return StockMovementModel.objects.filter(company_id=company_id, product_id=product_id).exists()
