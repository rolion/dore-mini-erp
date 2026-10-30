from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from .enums import PaymentMethod, PaymentRecordStatus


@dataclass
class Payment:
    """Pago de una compra. Inmutable tras crearse; nace de `Purchase.register_payment`."""

    id: UUID
    purchase_id: UUID
    amount: Decimal
    payment_method: PaymentMethod
    payment_date: date
    user_id: UUID | None
    user_name: str
    status: PaymentRecordStatus = PaymentRecordStatus.CONFIRMED
    created_at: datetime | None = None

    @property
    def reference(self) -> str:
        """Referencia interna provisional derivada del id (la numeración correlativa es otra task)."""
        return f'PAG-{self.id.hex[:8].upper()}'
