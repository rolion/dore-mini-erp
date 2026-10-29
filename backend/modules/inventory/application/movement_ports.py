from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ProductInfo:
    id: UUID
    name: str
    tracks_stock: bool
    unit_abbreviation: str | None
    allows_fractions: bool
    active: bool = True


class ProductDirectory(Protocol):
    """Datos de producto que Inventario necesita de Catálogo."""

    def get_products(self, product_ids: Iterable[UUID]) -> Mapping[UUID, ProductInfo]: ...

    def list_stock_products(self, search: str | None = None, active: bool | None = None) -> list[ProductInfo]:
        """Productos que controlan stock, por nombre."""
        ...


class InventoryPolicy(Protocol):
    """Política de inventario de la empresa."""

    def allow_negative_stock(self) -> bool: ...


class BlockNegativeStock:
    """Política por defecto: nunca se permite stock negativo."""

    def allow_negative_stock(self) -> bool:
        return False
