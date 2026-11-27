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


class _OrdersReport:
    """Reporte de pedidos de solo lectura: los filtros de la persona (fechas, período fiscal) se combinan con los
    criterios fijos de cada reporte (`scope`), y se devuelven los pedidos con los totales de todo el conjunto."""

    def __init__(self, repository: OrderRepository):
        self.repository = repository

    def scope(self, filters: OrderFilters) -> OrderFilters:
        raise NotImplementedError

    def execute(self, filters: OrderFilters | None = None) -> PaidOrdersReportData:
        scoped = self.scope(filters or OrderFilters())
        return PaidOrdersReportData(self.repository.list(scoped), self.repository.totals(scoped))


class PaidOrdersReport(_OrdersReport):
    """Ingresos por venta: pedidos entregados y pagados (sin filtros, todos hasta la fecha)."""

    def scope(self, filters: OrderFilters) -> OrderFilters:
        return replace(filters, statuses=(OrderStatus.DELIVERED,), payment_statuses=(PaymentStatus.PAID,),
                       has_balance=None, customer_id=None)


class ReceivableOrdersReport(_OrdersReport):
    """Pedidos por cobrar: no cancelados ni devueltos, con `total > paid_total` (criterio de «por cobrar» del ADR)."""

    def scope(self, filters: OrderFilters) -> OrderFilters:
        open_or_delivered = (OrderStatus.NEW, OrderStatus.IN_PREPARATION, OrderStatus.READY, OrderStatus.DELIVERED)
        return replace(filters, statuses=open_or_delivered, payment_statuses=(), has_balance=True, customer_id=None)
