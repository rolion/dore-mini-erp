"""Puertos que Purchases necesita de otros módulos. Su implementación vive en `infrastructure/adapters.py`."""
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ProductInfo:
    id: UUID
    name: str
    active: bool
    can_buy: bool
    unit_abbreviation: str | None
    allows_fractions: bool


class ProductCatalog(Protocol):
    def get_products(self, product_ids: Iterable[UUID]) -> dict[UUID, ProductInfo]: ...


@dataclass(frozen=True)
class Actor:
    user_id: UUID | None
    user_name: str


@dataclass(frozen=True)
class StockProductInfo:
    id: UUID
    name: str
    unit_abbreviation: str | None


@dataclass(frozen=True)
class StockWarehouse:
    id: UUID
    name: str
    is_default: bool


@dataclass(frozen=True)
class StockEntryMovement:
    id: UUID
    product_id: UUID
    product_name: str
    unit_abbreviation: str | None
    warehouse_id: UUID
    warehouse_name: str
    quantity: Decimal
    reference: str = ''
    status: str = 'confirmed'
    reversed_by_id: UUID | None = None
    reversed_by_reference: str = ''


class StockEntry(Protocol):
    """Entradas de inventario al recibir; integración opcional (solo con el módulo Inventario habilitado)."""

    def is_available(self) -> bool: ...

    def controlled_products(self, product_ids: Iterable[UUID]) -> dict[UUID, StockProductInfo]: ...

    def active_warehouses(self) -> list[StockWarehouse]: ...

    def register_entries(self, warehouse_id: UUID, lines: list[tuple[UUID, Decimal]], receipt_id: UUID,
                         reference: str, actor: Actor) -> None:
        """Una entrada por línea; lanza `PurchaseValidationError` con `warehouse_id` si el almacén no sirve."""
        ...

    def movements_for(self, receipt_id: UUID) -> list[StockEntryMovement]: ...

    def reverse_entries(self, receipt_id: UUID, reason: str, actor: Actor) -> None:
        """Revierte todas las entradas de la recepción, todas o ninguna; lanza `StockShortage` si falta saldo."""
        ...
