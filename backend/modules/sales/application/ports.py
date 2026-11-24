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


@dataclass(frozen=True)
class StockLink:
    movement_id: UUID
    product_id: UUID
    product_name: str
    unit: str | None
    quantity: Decimal
    warehouse_name: str
    reversed_by_id: UUID | None
    reversed_by_reference: str


@dataclass(frozen=True)
class ReversalEntry:
    """Asiento automático del pedido: el original y, si ya se contrarrestó, su contrasiento."""

    event: str
    entry_id: UUID
    accounting_date: date
    description: str
    total: Decimal
    reversed_by_id: UUID | None = None


class StockOutput(Protocol):
    """Integración opcional con Inventario: salidas al entregar. Con el módulo deshabilitado no hace nada."""

    def is_available(self) -> bool: ...

    def controlled_products(self, product_ids: Iterable[UUID]) -> dict[UUID, StockProductInfo]: ...

    def active_warehouses(self) -> list[StockWarehouse]: ...

    def allow_negative_stock(self) -> bool: ...

    def warehouse_names(self, warehouse_ids: Iterable[UUID]) -> dict[UUID, str]: ...

    def balances(self, warehouse_id: UUID, product_ids: Iterable[UUID]) -> dict[UUID, Decimal]: ...

    def register_outputs(self, warehouse_id: UUID, lines: list[tuple[UUID, Decimal]], order_id: UUID,
                         reference: str, actor: Actor) -> None:
        """Registra todas las salidas del pedido o ninguna; traduce los rechazos a errores de Ventas."""
        ...

    def output_for(self, order_id: UUID) -> StockOutputRecord | None: ...

    def reverse_outputs(self, order_id: UUID, reason: str, actor: Actor) -> None:
        """Reingresa al almacén de origen todas las salidas del pedido (todo o nada); sin salidas no hace nada."""
        ...

    def output_links(self, order_id: UUID) -> list['StockLink']:
        """Movimientos del pedido con su reverso (si ya se revirtió), para el historial del detalle."""
        ...


class DeliveryCosting(Protocol):
    """Costo de ventas al entregar (INV-01): valoriza las salidas al costo promedio y asienta Costo de ventas /
    Inventario en la transacción de quien llama. Rechaza la entrega con una excepción de Ventas si falta costo o
    configuración; sin cobertura contable no asienta ni exige nada."""

    def cost_delivery(self, order: object, lines: list[tuple[UUID, Decimal]], actor: Actor) -> None: ...

    def reverse_cost(self, order_id: UUID) -> None:
        """Contra-evento de las salidas valorizadas al costo de venta (devolución); sin Costeo no hace nada."""
        ...


AT_CONFIRM = 'AT_CONFIRM'  # reconocido al confirmar (lógica anterior, histórico)
AT_DELIVERY = 'AT_DELIVERY'  # reconocido al entregar


class SalesPosting(Protocol):
    """Integración opcional con Contabilidad: anticipos, reconocimiento al entregar, cobros y reversión.

    Todo ocurre dentro de la transacción de quien llama; rechaza la operación con una excepción de Ventas si no
    puede.
    Con el módulo deshabilitado o sin cobertura no hace nada nuevo (comportamiento anterior).
    """

    def recognition_state(self, order_id: UUID) -> str | None:
        """`AT_CONFIRM`, `AT_DELIVERY` o `None` (sin reconocimiento o con Contabilidad deshabilitada)."""
        ...

    def locks_total(self, order: object) -> bool:
        """¿El total del pedido debe permanecer estable (confirmado con cobertura o ya reconocido)?"""
        ...

    def has_posted_payments(self, order: object) -> bool:
        """¿Algún cobro del pedido tiene asiento (anticipo o cobro)?"""
        ...

    def record_payment(self, order: object, payment: object, actor: Actor, today: date) -> None:
        """Contabiliza un cobro por un único camino (anticipo, cobro o, sin cobertura, libro anterior)."""
        ...

    def recognize_delivery(self, order: object, actor: Actor) -> None:
        """Reconoce el ingreso al entregar y aplica los anticipos del pedido (una sola vez)."""
        ...

    def reverse_recognition(self, order: object, reason: str, actor: Actor, today: date) -> None:
        """Revierte el reconocimiento anterior (al confirmar) con las cuentas originales."""
        ...

    def reverse_payments(self, order: object, reason: str, actor: Actor, today: date) -> None:
        """Contrarresta los asientos de todos los cobros del pedido (reembolso externo declarado)."""
        ...

    def reverse_delivery(self, order: object, reason: str, actor: Actor, today: date) -> None:
        """Contrarresta ingreso y costo de venta (y el reconocimiento anterior) con las cuentas originales."""
        ...

    def reversal_entries(self, order: object) -> list[ReversalEntry]:
        """Asientos automáticos vinculados al pedido (venta, costo y cobros), con su contrasiento si existe."""
        ...
