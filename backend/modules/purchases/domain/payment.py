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
    # Instantánea de la clasificación de «pagos a proveedores» al registrar; nula en pagos anteriores.
    classification_id: UUID | None = None
    created_at: datetime | None = None

    def assign_classification(self, classification_id: UUID | None) -> None:
        """Fija la instantánea de la clasificación al registrar; después el pago no cambia."""
        self.classification_id = classification_id

    @property
    def reference(self) -> str:
        """Referencia interna provisional derivada del id (la numeración correlativa es otra task)."""
        return f'PAG-{self.id.hex[:8].upper()}'
