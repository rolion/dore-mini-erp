from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet, Sum

from modules.purchases.domain.enums import PaymentRecordStatus
from modules.purchases.domain.exceptions import PaymentConflict
from modules.purchases.domain.payment import Payment

from .mappers import payment_to_entity
from .models import PaymentModel


class DjangoPaymentRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _payments(self) -> QuerySet:
        return PaymentModel.objects.filter(company_id=self.company_id)

    def get(self, payment_id: UUID) -> Payment | None:
        model = self._payments().filter(pk=payment_id).first()
        return None if model is None else payment_to_entity(model)

    def save(self, payment: Payment) -> Payment:
        try:
            with transaction.atomic():  # savepoint: un id repetido no aborta la transacción del llamador
                model = PaymentModel.objects.create(
                    id=payment.id, company_id=self.company_id, purchase_id=payment.purchase_id,
                    amount=payment.amount, payment_method=payment.payment_method.value,
                    payment_date=payment.payment_date, status=payment.status.value, user_id=payment.user_id,
                    user_name=payment.user_name, classification_id=payment.classification_id,
                    debt_amount=payment.debt_amount, advance_amount=payment.advance_amount)
        except IntegrityError as exc:
            raise PaymentConflict() from exc
        return payment_to_entity(model)

    def list_for_purchase(self, purchase_id: UUID) -> list[Payment]:
        return [payment_to_entity(m) for m in self._payments().filter(purchase_id=purchase_id)]

    def _confirmed(self, purchase_id: UUID) -> QuerySet:
        return self._payments().filter(purchase_id=purchase_id, status=PaymentRecordStatus.CONFIRMED.value)

    def debt_paid_total(self, purchase_id: UUID) -> Decimal:
        """Suma de lo que los pagos confirmados liquidaron de deuda reconocida."""
        return self._confirmed(purchase_id).aggregate(total=Sum('debt_amount'))['total'] or Decimal('0.00')

    def advance_total(self, purchase_id: UUID) -> Decimal:
        """Suma de los anticipos a proveedores de los pagos confirmados."""
        return self._confirmed(purchase_id).aggregate(total=Sum('advance_amount'))['total'] or Decimal('0.00')

    def paid_total(self, purchase_id: UUID) -> Decimal:
        total = (self._payments().filter(purchase_id=purchase_id, status=PaymentRecordStatus.CONFIRMED.value)
                 .aggregate(total=Sum('amount'))['total'])
        return total if total is not None else Decimal('0.00')
