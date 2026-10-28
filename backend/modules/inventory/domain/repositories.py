from typing import Protocol, Sequence
from uuid import UUID

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
