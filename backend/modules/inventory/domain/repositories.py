from typing import Protocol, Sequence
from uuid import UUID

from .stock import RegisteredOpening, StockBalanceEntry, StockMovementEntry, StockOpening
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


class StockRepository(Protocol):
    """Movimientos y saldos de la empresa."""

    def atomic(self):
        """Gestor de contexto: todo lo que ocurra dentro es una sola transacción."""
        ...

    def lock_warehouse(self, warehouse_id: UUID) -> Warehouse | None:
        """El almacén bloqueado hasta el fin de la transacción (serializa aperturas), o `None`."""
        ...

    def find_opening(self, opening_id: UUID) -> RegisteredOpening | None: ...

    def products_with_history(self, warehouse_id: UUID, product_ids: list[UUID]) -> set[UUID]: ...

    def save_opening(self, opening: StockOpening, created_by_id: int | None) -> None: ...

    def list_balances(self, warehouse_id: UUID | None = None) -> Sequence[StockBalanceEntry]: ...

    def get_balance(self, warehouse_id: UUID, product_id: UUID) -> StockBalanceEntry | None: ...

    def list_movements(self, warehouse_id: UUID, product_id: UUID) -> Sequence[StockMovementEntry]: ...
