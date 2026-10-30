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


class ReceiptStatus(str, Enum):
    CONFIRMED = 'confirmed'
    REVERTED = 'reverted'
