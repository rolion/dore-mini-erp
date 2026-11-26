from contextlib import AbstractContextManager as ContextManager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence
from uuid import UUID

from .adjustment import StockAdjustment
from .lot import LotPosition, LotStatus, StockLot
from .movement import MovementKind, StockMovement
from .stock import StockBalanceEntry
from .warehouse import Warehouse


class WarehouseRepository(Protocol):
    def get(self, warehouse_id: UUID) -> Warehouse | None: ...

    def save(self, warehouse: Warehouse) -> Warehouse:
        """Persiste el almacén; si es el predeterminado deja de serlo el anterior. Valida nombre único."""
        ...

    def list(self, search: str | None = None, active: bool | None = None) -> Sequence[Warehouse]: ...

    def locked(self, warehouse_id: UUID) -> ContextManager[None]:
        """Transacción que bloquea la fila del almacén (la misma que serializa sus movimientos)."""
        ...

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
    source_id: str | None = None  # documento de origen concreto (con `source_type`)


class StockMovementRepository(Protocol):
    def locked(self, warehouse_id: UUID) -> ContextManager[None]:
        """Transacción que serializa los movimientos del almacén (bloquea su fila)."""
        ...

    def get(self, movement_id: UUID) -> StockMovement | None: ...

    def find_by_source(self, movement: StockMovement) -> StockMovement | None:
        """El movimiento equivalente (misma operación de origen, producto, almacén y tipo), si existe."""
        ...

    def balance(self, product_id: UUID, warehouse_id: UUID, *, lot_id: UUID | None = None,
                unlotted: bool = False) -> Decimal:
        """Saldo del producto en el almacén: físico (todo), de un lote (`lot_id`) o solo el stock sin lote."""
        ...

    def lot_has_movements(self, lot_id: UUID) -> bool: ...

    def insert(self, movement: StockMovement) -> StockMovement: ...

    def mark_reversed(self, movement_id: UUID) -> None: ...

    def list(self, filters: MovementFilters) -> Sequence[StockMovement]: ...

    def has_history(self, product_id: UUID) -> bool: ...

    def find_by_source_id(self, source_type: str, source_id: str) -> Sequence[StockMovement]:
        """Todos los movimientos de una operación de origen (p. ej. las líneas de una apertura)."""
        ...

    def products_with_history(self, warehouse_id: UUID, product_ids: Sequence[UUID]) -> set[UUID]:
        """Los productos indicados que ya tienen algún movimiento en el almacén."""
        ...

    def list_balances(self, warehouse_id: UUID | None = None, product_ids=None) -> Sequence[StockBalanceEntry]:
        """Existencias por producto y almacén (entradas menos salidas), con al menos un movimiento."""
        ...

    def has_nonzero_balance(self, warehouse_id: UUID) -> bool: ...

    def balances_for(self, warehouse_id: UUID, product_ids: Sequence[UUID],
                     unlotted: bool = False) -> dict[UUID, Decimal]:
        """Existencia de cada producto indicado en el almacén (0 si no tiene movimientos), en una consulta.

        Con `unlotted` solo cuenta el stock sin lote, que es el que puede consumir una salida sin lote.
        """
        ...


@dataclass(frozen=True)
class AdjustmentFilters:
    date_from: date | None = None
    date_to: date | None = None
    product_id: UUID | None = None
    warehouse_id: UUID | None = None


class StockAdjustmentRepository(Protocol):
    def get(self, adjustment_id: UUID) -> StockAdjustment | None: ...

    def insert(self, adjustment: StockAdjustment) -> StockAdjustment: ...

    def list(self, filters: AdjustmentFilters) -> Sequence[StockAdjustment]: ...


@dataclass(frozen=True)
class LotFilters:
    search: str | None = None  # parte del código
    product_id: UUID | None = None
    warehouse_id: UUID | None = None
    status: LotStatus | None = None
    with_stock: bool = False  # solo lotes con saldo físico distinto de cero


class StockLotRepository(Protocol):
    def get(self, lot_id: UUID) -> StockLot | None: ...

    def insert(self, lot: StockLot) -> StockLot: ...

    def save_release(self, lot: StockLot) -> None:
        """Persiste el paso a liberado (estado, fecha y persona)."""
        ...

    def get_position(self, lot_id: UUID) -> LotPosition | None: ...

    def list(self, filters: LotFilters) -> Sequence[LotPosition]: ...

    def for_product(self, product_id: UUID, warehouse_id: UUID) -> Sequence[LotPosition]: ...

    def pairs_with_lots(self) -> set[tuple[UUID, UUID]]:
        """Pares `(producto, almacén)` que tienen al menos un lote."""
        ...
