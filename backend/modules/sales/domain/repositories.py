from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence
from uuid import UUID

from .enums import OrderStatus, PaymentStatus, SalesChannel
from .order import Order

ORDER_DATE = 'order_date'
EXPECTED_DELIVERY_DATE = 'expected_delivery_date'

# Ordenamientos admitidos: por fecha de pedido (más recientes primero) o por entrega prevista (más próximas
# primero, sin fecha al final).
NEWEST_FIRST = '-order_date'
BY_EXPECTED_DELIVERY = 'expected_delivery_date'


@dataclass(frozen=True)
class OrderFilters:
    statuses: tuple[OrderStatus, ...] = ()
    payment_statuses: tuple[PaymentStatus, ...] = ()
    sales_channel: SalesChannel | None = None
    customer_id: UUID | None = None
    date_field: str = ORDER_DATE
    date_from: date | None = None
    date_to: date | None = None
    has_balance: bool | None = None
    ordering: str = NEWEST_FIRST


@dataclass(frozen=True)
class OrderSummary:
    """Modelo de lectura de la lista: usa los importes persistidos, sin cargar ítems ni pagos."""

    id: UUID
    customer_id: UUID | None
    sales_channel: SalesChannel
    order_date: date
    expected_delivery_date: date | None
    status: OrderStatus
    payment_status: PaymentStatus
    total: Decimal
    paid_total: Decimal

    @property
    def balance(self) -> Decimal:
        return self.total - self.paid_total

    @classmethod
    def from_order(cls, order: Order) -> 'OrderSummary':
        return cls(id=order.id, customer_id=order.customer_id, sales_channel=order.sales_channel,
                   order_date=order.order_date, expected_delivery_date=order.expected_delivery_date,
                   status=order.status, payment_status=order.payment_status, total=order.total,
                   paid_total=order.paid_total)


class OrderRepository(Protocol):
    def get(self, order_id: UUID) -> Order | None: ...

    def get_for_update(self, order_id: UUID) -> Order | None:
        """Como `get`, bloqueando la fila del pedido hasta el fin de la transacción en curso."""
        ...

    def save(self, order: Order) -> Order:
        """Persiste el agregado completo (ítems y pagos nuevos) y lo devuelve con los datos de la persistencia."""
        ...

    def list(self, filters: OrderFilters) -> Sequence[OrderSummary]:
        """Resúmenes de pedidos según los filtros y el orden indicados."""
        ...
