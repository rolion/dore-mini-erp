from uuid import UUID


class WarehouseValidationError(Exception):
    """Una o más reglas del almacén no se cumplen; `errors` mapea campo -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class WarehouseNotFound(Exception):
    def __init__(self, warehouse_id: UUID):
        super().__init__(f'Almacén {warehouse_id} no encontrado.')
        self.warehouse_id = warehouse_id


class WarehouseConflict(Exception):
    """La acción choca con el estado del almacén; `code` identifica el motivo y el mensaje se muestra tal cual."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
