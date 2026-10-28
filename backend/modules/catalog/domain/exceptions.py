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


class StockHistoryLocked(Exception):
    """El producto tiene movimientos de inventario: unidad y control de stock solo cambian por regularización."""

    def __init__(self):
        super().__init__(
            'Este producto tiene movimientos de inventario; no se puede cambiar el control de stock ni la '
            'unidad base. Usa el procedimiento de regularización.')


class UnitValidationError(Exception):
    """Una o más reglas de la unidad de medida no se cumplen; `errors` mapea campo -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class UnitNotFound(Exception):
    def __init__(self, unit_id: UUID):
        super().__init__(f'Unidad {unit_id} no encontrada.')
        self.unit_id = unit_id


class UnitInUse(Exception):
    """La unidad está asignada a productos: solo se puede activar o desactivar."""

    def __init__(self):
        super().__init__('Esta unidad ya está asignada a productos; solo se puede activar o desactivar.')
