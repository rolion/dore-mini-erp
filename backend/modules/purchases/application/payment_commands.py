from datetime import date
from decimal import Decimal
from uuid import UUID

from modules.purchases.domain.exceptions import PaymentConflict, PurchaseNotFound
from modules.purchases.domain.payment import Payment
from modules.purchases.domain.purchase import ZERO, split_payment
from modules.purchases.domain.repositories import (
    PaymentRepository,
    PurchaseRepository,
    PurchaseSettingsRepository,
    ReceiptRepository,
)

from .ports import Actor, ClassificationGateway, PurchasePosting


def split_for_payment(purchase, amount: Decimal, on: date, posting: PurchasePosting | None,
                      receipts: ReceiptRepository | None, payments: PaymentRepository) -> tuple[Decimal, Decimal]:
    """`(deuda, anticipo)` de un pago de `amount` en la fecha `on`.

    Solo se separa un anticipo si Contabilidad cubre la fecha (el anticipo existe en el libro); si no, todo cuenta
    como deuda pagada. Lee los acumulados bajo el bloqueo de la compra de quien llama.
    """
    if posting is None or receipts is None or not posting.covers(on):
        return amount, ZERO
    value = purchase.received_value(receipts.received_totals(purchase.id))
    paid = payments.debt_paid_total(purchase.id) + receipts.advance_applied_total(purchase.id)
    return split_payment(amount, value, paid)


class RegisterPayment:
    """Registra un pago de una compra confirmada, recalcula su estado de pago y lo contabiliza.

    Todo ocurre en la transacción del llamador con la compra bloqueada: dos pagos simultáneos se serializan y el
    segundo ve el acumulado del primero. Repetir el mismo `payment_id` devuelve el pago ya registrado
    (`created=False`) sin tocar los asientos. Con cobertura, el pago crea hasta dos asientos: la parte que liquida
    deuda reconocida (Debe Cuentas por pagar / Haber cuenta del método) y el exceso, un anticipo a proveedores.
    """

    def __init__(self, purchases: PurchaseRepository, payments: PaymentRepository,
                 settings: PurchaseSettingsRepository | None = None,
                 classifications: ClassificationGateway | None = None,
                 posting: PurchasePosting | None = None, receipts: ReceiptRepository | None = None):
        self.purchases = purchases
        self.payments = payments
        self.settings = settings
        self.classifications = classifications
        self.posting = posting
        self.receipts = receipts

    def _classification(self) -> UUID | None:
        """Instantánea opcional de «pagos a proveedores»: si hay una válida se guarda; nunca bloquea el pago."""
        if self.settings is None or self.classifications is None:
            return None
        classification_id = self.settings.payment_classification_id()
        if classification_id is None:
            return None
        info = self.classifications.describe([classification_id]).get(classification_id)
        if info is None or not info.active or info.direction != 'EXPENSE':
            return None
        return classification_id

    def execute(self, purchase_id: UUID, payment_id: UUID, amount: object, payment_method: object,
                payment_date: object, actor: Actor, today: date) -> tuple[Payment, bool]:
        purchase = self.purchases.get(purchase_id, for_update=True)
        if purchase is None:
            raise PurchaseNotFound(purchase_id)
        existing = self.payments.get(payment_id)
        if existing is not None:
            if existing.purchase_id != purchase_id:
                raise PaymentConflict()
            return existing, False
        payment = purchase.register_payment(payment_id, amount, payment_method, payment_date, today,
                                            self.payments.paid_total(purchase_id), actor.user_id, actor.user_name)
        payment.assign_classification(self._classification())
        debt, advance = split_for_payment(purchase, payment.amount, payment.payment_date, self.posting,
                                          self.receipts, self.payments)
        payment.allocate(debt)
        saved = self.payments.save(payment)
        self.purchases.save(purchase)
        if self.posting is not None and self.posting.covers(saved.payment_date):
            self.posting.record_payment(purchase, saved, debt, advance, actor)
        return saved, True
