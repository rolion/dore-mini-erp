from contextlib import AbstractContextManager as ContextManager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence
from uuid import UUID

from .movement import MovementKind, StockMovement
from .warehouse import Warehouse


class WarehouseRepository(Protocol):
    def get(self, warehouse_id: UUID) -> Warehouse | None: ...

    def save(self, warehouse: Warehouse) -> Warehouse:
        """Persiste el almacén; si es el predeterminado deja de serlo el anterior. Valida nombre único."""
        ...

    def list(self, search: str | None = None, active: bool | None = None) -> Sequence[Warehouse]: ...

    def ensure_default(self) -> None:
        """Si la empresa no tiene almacenes, crea el predeterminado (idempotente y seguro ante concurrencia)."""
        ...


@dataclass(frozen=True)
class MovementFilters:
    date_from: date | None = None
    date_to: date | None = None
    product_id: UUID | None = None
    warehouse_id: UUID | None = None
    kind: MovementKind | None = None
    source_type: str | None = None  # clase de origen, o 'none' para movimientos sin documento


class StockMovementRepository(Protocol):
    def locked(self, warehouse_id: UUID) -> ContextManager[None]:
        """Transacción que serializa los movimientos del almacén (bloquea su fila)."""
        ...

    def get(self, movement_id: UUID) -> StockMovement | None: ...

    def find_by_source(self, movement: StockMovement) -> StockMovement | None:
        """El movimiento equivalente (misma operación de origen, producto, almacén y tipo), si existe."""
        ...

    def balance(self, product_id: UUID, warehouse_id: UUID) -> Decimal: ...

    def insert(self, movement: StockMovement) -> StockMovement: ...

    def mark_reversed(self, movement_id: UUID) -> None: ...

    def list(self, filters: MovementFilters) -> Sequence[StockMovement]: ...

    def has_history(self, product_id: UUID) -> bool: ...

    def has_nonzero_balance(self, warehouse_id: UUID) -> bool: ...
