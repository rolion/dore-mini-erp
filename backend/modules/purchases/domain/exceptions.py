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
