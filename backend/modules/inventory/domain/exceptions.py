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


class OpeningValidationError(Exception):
    """La apertura no cumple una regla; `errors` mapea campo -> mensajes (y `lines` -> un dict por línea)."""

    def __init__(self, errors: dict[str, object]):
        super().__init__(errors)
        self.errors = errors


class StockHistoryExists(Exception):
    """Productos de la apertura que ya tienen movimientos en el almacén (INV-04); `indices` son posiciones de línea."""

    def __init__(self, indices: list[int], product_ids: list[UUID]):
        super().__init__('Algunos productos ya tienen movimientos en este almacén; corrígelos con un ajuste.')
        self.indices = indices
        self.product_ids = product_ids


class OpeningIdReused(Exception):
    def __init__(self):
        super().__init__('Esa clave de apertura ya se usó con otros datos.')


class OpeningConflict(Exception):
    """Una restricción de unicidad rechazó la apertura (carrera con otra escritura); el caso de uso la reinterpreta."""
