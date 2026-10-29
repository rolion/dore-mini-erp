from uuid import UUID


class SupplierValidationError(Exception):
    """Una o más reglas de dominio del proveedor no se cumplen; `errors` mapea campo -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class SupplierNotFound(Exception):
    def __init__(self, supplier_id: UUID):
        super().__init__(f'Proveedor {supplier_id} no encontrado.')
        self.supplier_id = supplier_id
