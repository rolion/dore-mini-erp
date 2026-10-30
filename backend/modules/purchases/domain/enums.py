from enum import Enum


class PurchaseStatus(str, Enum):
    DRAFT = 'draft'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'


class ReceptionStatus(str, Enum):
    NOT_RECEIVED = 'not_received'
    PARTIAL = 'partial'
    RECEIVED = 'received'


class PaymentStatus(str, Enum):
    UNPAID = 'unpaid'
    PARTIAL = 'partial'
    PAID = 'paid'


class InventoryMode(str, Enum):
    """Modo con que se confirmó una recepción: con Inventario habilitado o documental."""

    INVENTORY = 'inventory'
    DOCUMENTAL = 'documental'


class ReceiptStatus(str, Enum):
    CONFIRMED = 'confirmed'
    REVERTED = 'reverted'


class PaymentMethod(str, Enum):
    """Cómo se pagó la compra (mismos códigos que en Ventas y Gastos, pero propios de este módulo)."""

    CASH = 'CASH'
    QR = 'QR'
    BANK_TRANSFER = 'BANK_TRANSFER'
    CARD = 'CARD'
    OTHER = 'OTHER'


class PaymentRecordStatus(str, Enum):
    CONFIRMED = 'confirmed'
    VOIDED = 'voided'
