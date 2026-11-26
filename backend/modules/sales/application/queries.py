from collections.abc import Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from modules.sales.domain.enums import OrderStatus, PaymentStatus
from modules.sales.domain.exceptions import OrderNotFound
from modules.sales.domain.order import Order
from modules.sales.domain.repositories import OrderFilters, OrderRepository, OrderSummary, OrderTotals


class GetOrder:
    def __init__(self, repository: OrderRepository):
        self.repository = repository

    def execute(self, order_id: UUID) -> Order:
        order = self.repository.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        return order


class ListOrders:
    """Las consultas operativas (pendientes de entrega, por cobrar, por cliente, por fechas) son filtros."""

    def __init__(self, repository: OrderRepository):
        self.repository = repository

    def execute(self, filters: OrderFilters | None = None) -> Sequence[OrderSummary]:
        return self.repository.list(filters or OrderFilters())


@dataclass(frozen=True)
class PaidOrdersReportData:
    orders: Sequence[OrderSummary]
    totals: OrderTotals


class PaidOrdersReport:
    """Ingresos por venta: pedidos entregados y pagados (sin filtrar, todos hasta la fecha), con sus totales.

    Los filtros de la persona (fechas, período fiscal) se combinan con el estado y el pago fijos del reporte.
    """

    def __init__(self, repository: OrderRepository):
        self.repository = repository

    def execute(self, filters: OrderFilters | None = None) -> PaidOrdersReportData:
        scoped = replace(filters or OrderFilters(), statuses=(OrderStatus.DELIVERED,),
                         payment_statuses=(PaymentStatus.PAID,), has_balance=None, customer_id=None)
        return PaidOrdersReportData(self.repository.list(scoped), self.repository.totals(scoped))
