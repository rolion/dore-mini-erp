"""Entrega de pedidos con salida de inventario: líneas controladas, vista previa y selección de almacén."""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from modules.sales.domain.exceptions import OrderNotFound, OrderValidationError
from modules.sales.domain.order import Order
from modules.sales.domain.repositories import OrderRepository

from .ports import StockOutput, StockProductInfo, StockWarehouse


@dataclass(frozen=True)
class DeliveryLine:
    product: StockProductInfo
    quantity: Decimal
    available: Decimal | None  # None mientras no hay almacén elegido
    projected: Decimal | None

    @property
    def insufficient(self) -> bool:
        return self.projected is not None and self.projected < 0


@dataclass(frozen=True)
class DeliveryPreview:
    inventory_enabled: bool
    requires_stock_output: bool
    allow_negative_stock: bool
    warehouses: list[StockWarehouse]
    warehouse_id: UUID | None
    lines: list[DeliveryLine]


def controlled_lines(order: Order, stock: StockOutput) -> list[tuple[StockProductInfo, Decimal]]:
    """Cantidades a descontar por producto que controla stock (se suman las líneas repetidas); orden estable."""
    totals: dict[UUID, Decimal] = {}
    for item in order.items:
        totals[item.product_id] = totals.get(item.product_id, Decimal('0')) + Decimal(item.quantity)
    controlled = stock.controlled_products(totals)
    return [(controlled[product_id], quantity) for product_id, quantity in totals.items()
            if product_id in controlled]


def suggested_warehouse(warehouses: list[StockWarehouse], requested: UUID | None) -> UUID | None:
    """El elegido por la persona (si es válido); si no, el único activo o el predeterminado."""
    if requested is not None:
        if all(w.id != requested for w in warehouses):
            raise OrderValidationError({'warehouse_id': ['El almacén no existe o está inactivo.']})
        return requested
    if len(warehouses) == 1:
        return warehouses[0].id
    return next((w.id for w in warehouses if w.is_default), None)


class PreviewOrderDelivery:
    """Qué pasaría al entregar: solo lectura e informativo (el servidor revalida al confirmar)."""

    def __init__(self, repository: OrderRepository, stock: StockOutput):
        self.repository = repository
        self.stock = stock

    def execute(self, order_id: UUID, warehouse_id: UUID | None = None) -> DeliveryPreview:
        order = self.repository.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        order.ensure_deliverable()
        if not self.stock.is_available():
            return DeliveryPreview(False, False, False, [], None, [])
        planned = controlled_lines(order, self.stock)
        if not planned:
            return DeliveryPreview(True, False, self.stock.allow_negative_stock(), [], None, [])
        warehouses = self.stock.active_warehouses()
        selected = suggested_warehouse(warehouses, warehouse_id)
        balances = self.stock.balances(selected, [p.id for p, _ in planned]) if selected else {}
        lines = []
        for product, quantity in planned:
            available = balances.get(product.id, Decimal('0')) if selected else None
            lines.append(DeliveryLine(product, quantity, available,
                                      None if available is None else available - quantity))
        return DeliveryPreview(True, True, self.stock.allow_negative_stock(), warehouses, selected, lines)
