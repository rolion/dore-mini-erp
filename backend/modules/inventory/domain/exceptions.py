from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
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


class MovementValidationError(Exception):
    """Datos del movimiento inválidos; `errors` mapea campo -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class MovementNotFound(Exception):
    def __init__(self, movement_id: UUID):
        super().__init__(f'Movimiento {movement_id} no encontrado.')
        self.movement_id = movement_id


class MovementConflict(Exception):
    """La operación choca con el libro (cantidad distinta en un reintento, saldo insuficiente, ya revertido)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Shortage:
    """Una línea sin saldo suficiente: producto, cantidad pedida y existencia vigente."""

    product_id: UUID
    requested: Decimal
    available: Decimal


class InsufficientStock(MovementConflict):
    """Salida mayor que el saldo con la política de stock negativo bloqueada; lleva los datos para explicarla.

    `product_id`/`requested`/`available` describen la primera línea faltante; `shortages` las lista todas
    (una salida en lote informa todas las líneas sin saldo).
    """

    def __init__(self, message: str, *, product_id: UUID, warehouse_id: UUID, requested, available,
                 shortages: Sequence[Shortage] | None = None):
        super().__init__('insufficient_stock', message)
        self.product_id = product_id
        self.warehouse_id = warehouse_id
        self.requested = requested
        self.available = available
        self.shortages = tuple(shortages) if shortages else (Shortage(product_id, requested, available),)


class OpeningValidationError(Exception):
    """La apertura no cumple una regla; `errors` mapea campo -> mensajes (y `lines` -> un dict por línea)."""

    def __init__(self, errors: dict[str, object]):
        super().__init__(errors)
        self.errors = errors


class StockHistoryExists(Exception):
    """Productos de la apertura que ya tienen movimientos en el almacén; `indices` son posiciones de línea."""

    def __init__(self, indices: list[int], product_ids: list[UUID]):
        super().__init__('Algunos productos ya tienen movimientos en este almacén; corrígelos con un ajuste.')
        self.indices = indices
        self.product_ids = product_ids


class OpeningIdReused(Exception):
    def __init__(self):
        super().__init__('Esa clave de apertura ya se usó con otros datos.')


class AdjustmentValidationError(Exception):
    """El ajuste no cumple una regla; `errors` mapea campo -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class AdjustmentNotFound(Exception):
    def __init__(self, adjustment_id: UUID):
        super().__init__(f'Ajuste {adjustment_id} no encontrado.')
        self.adjustment_id = adjustment_id


class AdjustmentConflict(Exception):
    """El ajuste choca con el estado actual; `code` identifica el motivo y el mensaje se muestra tal cual."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class NoDifference(AdjustmentConflict):
    def __init__(self):
        super().__init__('no_difference', 'Sin diferencia: la cantidad contada coincide con el saldo.')


class BalanceChanged(AdjustmentConflict):
    """El saldo cambió desde el conteo: hay que revisar la diferencia con el saldo vigente."""

    def __init__(self, current_balance):
        super().__init__('balance_changed', 'El saldo cambió desde el conteo; revisa la diferencia y confirma de nuevo.')
        self.current_balance = current_balance


class AdjustmentIdReused(AdjustmentConflict):
    def __init__(self):
        super().__init__('adjustment_id_reused', 'Esa clave de ajuste ya se usó con otros datos.')


class StockPositionNotFound(Exception):
    """El producto no existe, es de otra empresa o no controla stock."""

    def __init__(self, product_id: UUID):
        super().__init__(f'Producto {product_id} sin control de stock o inexistente.')
        self.product_id = product_id
