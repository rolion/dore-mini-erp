from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class WarehouseActivity(Protocol):
    """Datos de otros contextos que impiden desactivar un almacén (saldos, recepciones pendientes)."""

    def has_nonzero_balance(self, warehouse_id: UUID) -> bool: ...

    def has_pending_receipts(self, warehouse_id: UUID) -> bool: ...


@dataclass(frozen=True)
class ProductInfo:
    """Lo que Inventario necesita de un producto de Catálogo."""

    id: UUID
    name: str
    active: bool
    tracks_stock: bool
    unit_name: str | None
    unit_abbreviation: str | None
    allows_fractions: bool


class ProductCatalog(Protocol):
    """Productos de la empresa por id; los inexistentes (o de otra empresa) no aparecen."""

    def get_products(self, product_ids: list[UUID]) -> dict[UUID, ProductInfo]: ...
