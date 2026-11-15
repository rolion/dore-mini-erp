from datetime import date
from uuid import UUID

from modules.purchases.domain.exceptions import (
    INVALID,
    NOT_CONFIGURED,
    PaymentClassificationError,
    PaymentConflict,
    PurchaseNotFound,
)
from modules.purchases.domain.payment import Payment
from modules.purchases.domain.repositories import PaymentRepository, PurchaseRepository, PurchaseSettingsRepository

from .ports import Actor, ClassificationGateway


HINT = 'Configúrela en Contabilidad → Configuración → Egresos.'


class RegisterPayment:
    """Registra un pago de una compra confirmada y recalcula su estado de pago.

    Todo ocurre en la transacción del llamador con la compra bloqueada: dos pagos simultáneos se serializan y el
    segundo ve el acumulado del primero. Repetir el mismo `payment_id` devuelve el pago ya registrado
    (`created=False`).
    """

    def __init__(self, purchases: PurchaseRepository, payments: PaymentRepository,
                 settings: PurchaseSettingsRepository | None = None,
                 classifications: ClassificationGateway | None = None):
        self.purchases = purchases
        self.payments = payments
        self.settings = settings
        self.classifications = classifications

    def _classification(self, payment_date) -> UUID | None:
        """Instantánea de «pagos a proveedores»; con Contabilidad cubriendo la fecha, sin ella no se registra."""
        if self.settings is None or self.classifications is None:
            return None
        covered = self.classifications.is_covered(payment_date)
        classification_id = self.settings.payment_classification_id()
        if classification_id is None:
            if covered:
                raise PaymentClassificationError(NOT_CONFIGURED, f'Falta la clasificación de pagos a proveedores. {HINT}')
            return None
        info = self.classifications.describe([classification_id]).get(classification_id)
        if info is None or not info.active or info.direction != 'EXPENSE':
            if covered:
                raise PaymentClassificationError(
                    INVALID, f'La clasificación de pagos a proveedores está inactiva o no es de egreso. {HINT}')
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
        payment.classification_id = self._classification(payment.payment_date)
        saved = self.payments.save(payment)
        self.purchases.save(purchase)
        return saved, True
