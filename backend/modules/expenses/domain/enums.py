from enum import Enum


class ExpenseStatus(str, Enum):
    """Vigente o anulado; anular es irreversible."""

    ACTIVE = 'ACTIVE'
    VOIDED = 'VOIDED'


class PaymentMethod(str, Enum):
    """Cómo se pagó el gasto (mismos códigos que en Sales, pero propios de este módulo)."""

    CASH = 'CASH'
    QR = 'QR'
    BANK_TRANSFER = 'BANK_TRANSFER'
    CARD = 'CARD'
    OTHER = 'OTHER'
