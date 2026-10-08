from collections.abc import Sequence
from uuid import UUID

from modules.sales.domain.exceptions import OrderNotFound
from modules.sales.domain.order import Order
from modules.sales.domain.repositories import OrderFilters, OrderRepository, OrderSummary


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
