from uuid import UUID


class CustomerValidationError(Exception):
    """Una o más reglas de dominio del cliente no se cumplen; `errors` mapea campo -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class CustomerNotFound(Exception):
    def __init__(self, customer_id: UUID):
        super().__init__(f'Cliente {customer_id} no encontrado.')
        self.customer_id = customer_id
