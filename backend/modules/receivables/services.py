"""Fachada pública de solo lectura de Cobros para otros módulos (p. ej. Contabilidad).

Devuelve DTO inmutables, nunca modelos. La empresa es siempre el primer argumento.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from modules.receivables.infrastructure.django.models import PaymentModel


@dataclass(frozen=True)
class HistoricalPayment:
    id: UUID
    amount: Decimal
    method: str
    payment_date: date
    document_ref: str  # número de la fuente (proforma)
    receipt_number: str
    reference: str
    recorded_by: int | None
    recorded_by_name: str
    document_state: str = ''  # Cobros no guarda pagos anulados: sin estado


def list_historical_payments(company_id: UUID, date_from: date | None = None,
                             date_to: date | None = None) -> tuple[HistoricalPayment, ...]:
    """Pagos de la empresa por fecha efectiva (inclusive). Solo lectura."""
    rows = PaymentModel.objects.filter(company_id=company_id).select_related('obligation')
    if date_from:
        rows = rows.filter(payment_date__gte=date_from)
    if date_to:
        rows = rows.filter(payment_date__lte=date_to)
    return tuple(
        HistoricalPayment(id=p.id, amount=p.amount, method=p.payment_method, payment_date=p.payment_date,
                          document_ref=p.obligation.source_number, receipt_number=p.receipt_number,
                          reference=p.reference, recorded_by=p.recorded_by, recorded_by_name=p.recorded_by_name)
        for p in rows.order_by('payment_date', 'created_at', 'id')
    )
