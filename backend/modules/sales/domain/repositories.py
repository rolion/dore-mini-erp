from dataclasses import dataclass
from datetime import date
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


class OrderRepository(Protocol):
    def get(self, order_id: UUID) -> Order | None: ...

    def get_for_update(self, order_id: UUID) -> Order | None:
        """Como `get`, bloqueando la fila del pedido hasta el fin de la transacción en curso."""
        ...

    def save(self, order: Order) -> Order:
        """Persiste el agregado completo (ítems y pagos nuevos) y lo devuelve con los datos de la persistencia."""
        ...

    def list(self, filters: OrderFilters) -> Sequence[Order]:
        """Pedidos (sin ítems ni pagos cargados necesariamente) según los filtros y el orden indicados."""
        ...
