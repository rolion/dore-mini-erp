from uuid import UUID

from modules.purchases.domain.exceptions import PurchaseNotFound
from modules.purchases.domain.payment import Payment
from modules.purchases.domain.repositories import PaymentRepository, PurchaseRepository


class ListPayments:
    def __init__(self, purchases: PurchaseRepository, payments: PaymentRepository):
        self.purchases = purchases
        self.payments = payments

    def execute(self, purchase_id: UUID) -> list[Payment]:
        if self.purchases.get(purchase_id) is None:
            raise PurchaseNotFound(purchase_id)
        return list(self.payments.list_for_purchase(purchase_id))
