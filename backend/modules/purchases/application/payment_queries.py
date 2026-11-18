from datetime import date
from uuid import UUID

from modules.purchases.domain.exceptions import PurchaseNotFound
from modules.purchases.domain.payment import Payment
from modules.purchases.domain.repositories import PaymentRepository, PurchaseRepository, ReceiptRepository

from .payment_commands import split_for_payment
from .ports import PaymentPreview, PurchasePosting


class ListPayments:
    def __init__(self, purchases: PurchaseRepository, payments: PaymentRepository):
        self.purchases = purchases
        self.payments = payments

    def execute(self, purchase_id: UUID) -> list[Payment]:
        if self.purchases.get(purchase_id) is None:
            raise PurchaseNotFound(purchase_id)
        return list(self.payments.list_for_purchase(purchase_id))


class PreviewPayment:
    """Asiento previsto de un pago, sin escribir nada. Valida monto, método y fecha como el alta del pago."""

    def __init__(self, purchases: PurchaseRepository, payments: PaymentRepository, receipts: ReceiptRepository,
                 posting: PurchasePosting):
        self.purchases = purchases
        self.payments = payments
        self.receipts = receipts
        self.posting = posting

    def execute(self, purchase_id: UUID, amount: object, payment_method: object, payment_date: object,
                today: date) -> PaymentPreview:
        purchase = self.purchases.get(purchase_id)
        if purchase is None:
            raise PurchaseNotFound(purchase_id)
        # Valida como el alta (lanza `PurchaseValidationError`); el pago y el cambio de estado se descartan.
        payment = purchase.register_payment(UUID(int=0), amount, payment_method, payment_date, today,
                                            self.payments.paid_total(purchase_id), None, '')
        debt, advance = split_for_payment(purchase, payment.amount, payment.payment_date, self.posting,
                                          self.receipts, self.payments)
        return self.posting.preview_payment(purchase, payment.amount, payment.payment_method.value,
                                            payment.payment_date, debt, advance)
