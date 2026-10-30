from decimal import Decimal
from uuid import UUID


class SupplierValidationError(Exception):
    """Una o más reglas de dominio del proveedor no se cumplen; `errors` mapea campo -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class PurchaseValidationError(Exception):
    """Reglas de la compra incumplidas; `errors` mapea campo -> mensajes y `items` -> un dict por línea."""

    def __init__(self, errors: dict[str, object]):
        super().__init__(errors)
        self.errors = errors


class ReceiptInventoryModeAlreadySet(Exception):
    """El modo de inventario de una recepción se fija una sola vez, al confirmarla."""


class PurchaseNotFound(Exception):
    def __init__(self, purchase_id: UUID):
        super().__init__(f'Compra {purchase_id} no encontrada.')
        self.purchase_id = purchase_id


class PurchaseNotEditable(Exception):
    """La compra ya no está en borrador."""


class PurchaseInvalidTransition(Exception):
    """La transición pedida no es posible desde el estado actual (p. ej. confirmar una compra cancelada)."""


class PurchaseCancellationBlocked(Exception):
    """La compra ya tiene recepciones o pagos: no puede cancelarse."""


class PurchaseNotReceivable(Exception):
    """Solo una compra confirmada admite recepciones."""


class PurchaseNotPayable(Exception):
    """Solo una compra confirmada admite pagos."""


class PaymentConflict(Exception):
    """El identificador del pago ya pertenece a otra compra."""


class ReceiptAlreadyReverted(Exception):
    """La recepción ya fue revertida: no se puede revertir otra vez."""


class ReceiptInventoryUnavailable(Exception):
    """La recepción movió stock y el módulo Inventario está deshabilitado: no hay libro que corregir."""


class StockShortage(Exception):
    """Revertir las entradas dejaría stock negativo bloqueado; `shortages` es `(producto, solicitado, saldo)`."""

    def __init__(self, warehouse_id: UUID, shortages: list[tuple[UUID, Decimal, Decimal]]):
        super().__init__('No hay saldo suficiente para revertir la recepción.')
        self.warehouse_id = warehouse_id
        self.shortages = shortages


class ReceiptNotFound(Exception):
    def __init__(self, receipt_id: UUID):
        super().__init__(f'Recepción {receipt_id} no encontrada.')
        self.receipt_id = receipt_id


class ReceiptConflict(Exception):
    """El identificador de la recepción ya pertenece a otra compra."""


class SupplierNotFound(Exception):
    def __init__(self, supplier_id: UUID):
        super().__init__(f'Proveedor {supplier_id} no encontrado.')
        self.supplier_id = supplier_id
