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
