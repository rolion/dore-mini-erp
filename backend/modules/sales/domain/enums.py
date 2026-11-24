from enum import Enum


class OrderStatus(str, Enum):
    """Avance logístico del pedido (independiente del cobro)."""

    NEW = 'NEW'
    IN_PREPARATION = 'IN_PREPARATION'
    READY = 'READY'
    DELIVERED = 'DELIVERED'
    CANCELLED = 'CANCELLED'
    RETURNED = 'RETURNED'


class PaymentStatus(str, Enum):
    """Estado de cobro; siempre derivado de los pagos del pedido.

    REFUNDED: el pedido se canceló o devolvió con cobros y la persona confirmó el reembolso fuera de PocketBiz.
    """

    PENDING = 'PENDING'
    PARTIAL = 'PARTIAL'
    PAID = 'PAID'
    REFUNDED = 'REFUNDED'


class SalesChannel(str, Enum):
    WHATSAPP = 'WHATSAPP'
    FACEBOOK = 'FACEBOOK'
    INSTAGRAM = 'INSTAGRAM'
    STORE = 'STORE'
    FAIR = 'FAIR'
    OTHER = 'OTHER'


class PaymentMethod(str, Enum):
    CASH = 'CASH'
    QR = 'QR'
    BANK_TRANSFER = 'BANK_TRANSFER'
    CARD = 'CARD'
    OTHER = 'OTHER'
