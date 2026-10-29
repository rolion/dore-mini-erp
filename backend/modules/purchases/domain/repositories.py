from typing import Protocol, Sequence
from uuid import UUID

from .supplier import Supplier


class SupplierRepository(Protocol):
    def get(self, supplier_id: UUID) -> Supplier | None: ...

    def save(self, supplier: Supplier) -> Supplier:
        """Persiste el proveedor y lo devuelve con los datos que asigna la persistencia (timestamps)."""
        ...

    def list(self, search: str | None = None, active: bool | None = None) -> Sequence[Supplier]:
        """Proveedores ordenados por nombre e id; `search` es coincidencia parcial por nombre o identificación."""
        ...
