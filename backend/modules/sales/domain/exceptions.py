from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


class OrderValidationError(Exception):
    """Un dato enviado no cumple una regla de dominio; `errors` mapea campo -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class OrderRuleViolation(Exception):
    """El pedido está en un estado que no admite la acción; no es atribuible a un campo. `code` es estable."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class OrderNotFound(Exception):
    def __init__(self, order_id: UUID):
        super().__init__(f'Pedido {order_id} no encontrado.')
        self.order_id = order_id


class OrderItemNotFound(Exception):
    def __init__(self, item_id: UUID):
        super().__init__(f'Ítem {item_id} no encontrado.')
        self.item_id = item_id


@dataclass(frozen=True)
class ShortLine:
    """Una línea de la entrega sin existencia suficiente en el almacén."""

    product_id: UUID
    product_name: str
    unit: str | None
    requested: Decimal
    available: Decimal


class InsufficientStockForDelivery(OrderRuleViolation):
    """La política de la empresa bloquea el stock negativo y alguna línea no alcanza; no se entrega nada."""

    def __init__(self, message: str, warehouse_id: UUID, warehouse_name: str, lines: list[ShortLine]):
        super().__init__('insufficient_stock', message)
        self.warehouse_id = warehouse_id
        self.warehouse_name = warehouse_name
        self.lines = lines
