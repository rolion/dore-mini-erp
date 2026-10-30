from datetime import date
from uuid import UUID

from modules.purchases.domain.exceptions import PaymentConflict, PurchaseNotFound
from modules.purchases.domain.payment import Payment
from modules.purchases.domain.repositories import PaymentRepository, PurchaseRepository

from .ports import Actor


class RegisterPayment:
    """Registra un pago de una compra confirmada y recalcula su estado de pago.

    Todo ocurre en la transacción del llamador con la compra bloqueada: dos pagos simultáneos se serializan y el
    segundo ve el acumulado del primero. Repetir el mismo `payment_id` devuelve el pago ya registrado
    (`created=False`).
    """

    def __init__(self, purchases: PurchaseRepository, payments: PaymentRepository):
        self.purchases = purchases
        self.payments = payments

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
        saved = self.payments.save(payment)
        self.purchases.save(purchase)
        return saved, True
