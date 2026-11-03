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
    category: str | None = None
    can_buy: bool = False
    can_sell: bool = True


class ProductDirectory(Protocol):
    """Datos de producto que Inventario necesita de Catálogo."""

    def get_products(self, product_ids: Iterable[UUID]) -> Mapping[UUID, ProductInfo]: ...

    def list_stock_products(self, search: str | None = None, active: bool | None = None,
                            category: str | None = None, can_buy: bool | None = None,
                            can_sell: bool | None = None) -> list[ProductInfo]:
        """Productos que controlan stock, por nombre (`category='none'` = sin clasificar)."""
        ...


class InventoryPolicy(Protocol):
    """Política de inventario de la empresa."""

    def allow_negative_stock(self) -> bool: ...


class BlockNegativeStock:
    """Política por defecto: nunca se permite stock negativo."""

    def allow_negative_stock(self) -> bool:
        return False


def apply_valuation(policy: object, movement, value=None) -> None:
    """Valora el movimiento (inventario valorado) justo antes de insertarlo, en la misma sección crítica.

    La política de producción lo implementa (`value_movement`); las políticas simples de las pruebas no valoran.
    """
    hook = getattr(policy, 'value_movement', None)
    if hook is not None:
        hook(movement, value)
