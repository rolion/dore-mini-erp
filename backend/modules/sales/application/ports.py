"""Puertos que Sales necesita del exterior: otros módulos y el reloj.

Las implementaciones viven en `infrastructure/` (adaptadores sobre las fachadas `services.py` de Catalog y Customers).
"""
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ProductInfo:
    id: UUID
    name: str
    sale_price: Decimal | None
    active: bool
    can_sell: bool = True


@dataclass(frozen=True)
class CustomerInfo:
    id: UUID
    name: str
    active: bool


class ProductCatalog(Protocol):
    def get_product_for_sale(self, product_id: UUID) -> ProductInfo | None: ...


class CustomerDirectory(Protocol):
    def is_available(self) -> bool: ...

    def get_customer_for_sale(self, customer_id: UUID) -> CustomerInfo | None: ...

    def get_customer_names(self, customer_ids: Iterable[UUID]) -> dict[UUID, str]: ...


class SalesSettingsReader(Protocol):
    def max_discount_percent(self) -> Decimal: ...


class Clock(Protocol):
    def today(self) -> date: ...

    def now(self) -> datetime: ...


@dataclass(frozen=True)
class Actor:
    """Quién ejecuta la acción (queda en los movimientos de inventario)."""

    user_id: UUID | None
    user_name: str


@dataclass(frozen=True)
class StockWarehouse:
    id: UUID
    name: str
    is_default: bool


@dataclass(frozen=True)
class StockProductInfo:
    """Producto que controla stock, con su unidad base."""

    id: UUID
    name: str
    unit: str | None


@dataclass(frozen=True)
class StockOutputMovement:
    id: UUID
    product_id: UUID
    product_name: str
    unit: str | None
    quantity: Decimal


@dataclass(frozen=True)
class StockOutputRecord:
    """Salida de inventario de un pedido entregado, leída del libro de movimientos."""

    reference: str
    warehouse_id: UUID
    warehouse_name: str
    occurred_at: datetime
    user_name: str
    movements: list[StockOutputMovement]


class StockOutput(Protocol):
    """Integración opcional con Inventario: salidas al entregar. Con el módulo deshabilitado no hace nada."""

    def is_available(self) -> bool: ...

    def controlled_products(self, product_ids: Iterable[UUID]) -> dict[UUID, StockProductInfo]: ...

    def active_warehouses(self) -> list[StockWarehouse]: ...

    def allow_negative_stock(self) -> bool: ...

    def balances(self, warehouse_id: UUID, product_ids: Iterable[UUID]) -> dict[UUID, Decimal]: ...

    def register_outputs(self, warehouse_id: UUID, lines: list[tuple[UUID, Decimal]], order_id: UUID,
                         reference: str, actor: Actor) -> None:
        """Registra todas las salidas del pedido o ninguna; traduce los rechazos a errores de Ventas."""
        ...

    def output_for(self, order_id: UUID) -> StockOutputRecord | None: ...
