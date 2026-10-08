from uuid import UUID


class ProductValidationError(Exception):
    """Una o más reglas de dominio del producto no se cumplen; `errors` mapea campo -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class ProductNotFound(Exception):
    def __init__(self, product_id: UUID):
        super().__init__(f'Producto {product_id} no encontrado.')
        self.product_id = product_id
