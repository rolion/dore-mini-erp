from datetime import date
from uuid import UUID

from django.db import IntegrityError, transaction

from modules.receivables.domain.obligation import Allocation, Obligation, Payment, PaymentMethod
from modules.receivables.infrastructure.django.models import (
    AllocationModel, ObligationModel, PaymentModel, ReceiptCounterModel,
)


def _payment(row: PaymentModel) -> Payment:
    allocations = tuple(Allocation(a.lineage_id, a.line_id, a.description, a.amount) for a in row.allocations.all())
    return Payment(row.id, row.receipt_number, row.amount, PaymentMethod(row.payment_method), row.payment_date,
                   row.reference, allocations, row.recorded_by, row.recorded_by_name, row.created_at,
                   row.idempotency_key)


def to_domain(row: ObligationModel) -> Obligation:
    return Obligation(row.id, row.source_kind, row.source_number, row.customer_id, row.customer_name,
                      [_payment(p) for p in row.payments.all()], row.created_at)


class DjangoObligationRepository:
    """Toda consulta filtra por la empresa recibida."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _qs(self):
        return ObligationModel.objects.filter(company_id=self.company_id).prefetch_related(
            'payments__allocations')

    def find(self, kind: str, number: str) -> Obligation | None:
        row = self._qs().filter(source_kind=kind, source_number=number).first()
        return to_domain(row) if row else None

    def lock_or_create(self, empty: Obligation) -> Obligation:
        """Obtiene (creando si falta) la obligación del compromiso y bloquea su fila (INV-02, INV-07)."""
        key = {'company_id': self.company_id, 'source_kind': empty.source_kind, 'source_number': empty.source_number}
        if not ObligationModel.objects.filter(**key).exists():
            try:
                with transaction.atomic():  # savepoint: la carrera por el único no rompe la transacción externa
                    ObligationModel.objects.create(id=empty.id, customer_id=empty.customer_id,
                                                   customer_name=empty.customer_name, **key)
            except IntegrityError:
                pass
        ObligationModel.objects.select_for_update().get(**key)
        return self.find(empty.source_kind, empty.source_number)

    def find_payment_by_key(self, key: UUID) -> tuple[PaymentModel, str] | None:
        row = PaymentModel.objects.filter(company_id=self.company_id, idempotency_key=key).select_related(
            'obligation').prefetch_related('allocations').first()
        return (row, row.payload_hash) if row else None

    def next_receipt(self) -> str:
        """Consecutivo por empresa; el bloqueo de la fila del contador serializa pagos concurrentes."""
        ReceiptCounterModel.objects.get_or_create(company_id=self.company_id)
        counter = ReceiptCounterModel.objects.select_for_update().get(company_id=self.company_id)
        counter.last_number += 1
        counter.save(update_fields=['last_number'])
        return f'CB-{counter.last_number:06d}'

    def add_payment(self, obligation: Obligation, payment: Payment, payload_hash: str) -> None:
        """Los pagos y sus imputaciones se insertan una vez y nunca se editan (INV-09)."""
        row = PaymentModel.objects.create(
            id=payment.id, company_id=self.company_id, obligation_id=obligation.id,
            receipt_number=payment.receipt_number, amount=payment.amount, payment_method=payment.payment_method.value,
            payment_date=payment.payment_date, reference=payment.reference, recorded_by=payment.recorded_by,
            recorded_by_name=payment.recorded_by_name, idempotency_key=payment.idempotency_key,
            payload_hash=payload_hash, created_at=payment.created_at)
        AllocationModel.objects.bulk_create([
            AllocationModel(payment=row, lineage_id=a.lineage_id, line_id=a.line_id, description=a.description,
                            amount=a.amount) for a in payment.allocations])

    def search(self, *, customer_id: UUID | None = None, date_from: date | None = None,
               date_to: date | None = None) -> list[Obligation]:
        qs = self._qs()
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return [to_domain(r) for r in qs]
