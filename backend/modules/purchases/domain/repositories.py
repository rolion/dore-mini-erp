from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence
from uuid import UUID

from .enums import PurchaseStatus
from .purchase import Purchase
from .supplier import Supplier


@dataclass(frozen=True)
class PurchaseSummary:
    """Fila de la lista de compras: datos de cabecera, total y número de líneas."""

    id: UUID
    purchase_date: date
    supplier_id: UUID
    supplier_name: str
    external_reference: str
    total: Decimal
    status: PurchaseStatus
    items_count: int


class PurchaseRepository(Protocol):
    def get(self, purchase_id: UUID, for_update: bool = False) -> Purchase | None: ...

    def save(self, purchase: Purchase) -> Purchase:
        """Persiste la compra con sus líneas (las reemplaza) y la devuelve con los datos que asigna la persistencia."""
        ...

    def list(self, supplier_id: UUID | None = None) -> Sequence[PurchaseSummary]:
        """Compras de la empresa: fecha desc, creación desc, id; opcionalmente de un proveedor."""
        ...


class SupplierRepository(Protocol):
    def get(self, supplier_id: UUID) -> Supplier | None: ...

    def save(self, supplier: Supplier) -> Supplier:
        """Persiste el proveedor y lo devuelve con los datos que asigna la persistencia (timestamps)."""
        ...

    def list(self, search: str | None = None, active: bool | None = None) -> Sequence[Supplier]:
        """Proveedores ordenados por nombre e id; `search` es coincidencia parcial por nombre o identificación."""
        ...
