"""Adaptadores de la regularización: leen Ventas y Cobros solo por su fachada `services` y escriben en el libro."""
import hashlib
from datetime import date, datetime
from uuid import UUID

from django.db import connection, transaction

from modules.accounting import services as accounting
from modules.accounting.application.regularize import LedgerRejected
from modules.accounting.domain.entry import Entry
from modules.accounting.domain.regularization import Item, SourcePayment
from modules.accounting.infrastructure.django.repositories import DjangoEntryRepository
from modules.receivables import services as receivables
from modules.sales import services as sales

_LOCK_NAMESPACE = 0x4C45  # "LE": libro de entradas


class SalesPaymentSource:
    def list_payments(self, company_id: UUID, date_from: date | None, date_to: date | None) -> list[SourcePayment]:
        return [
            SourcePayment('PRODUCT', p.id, p.amount, p.method, p.payment_date, document_ref=p.document_ref,
                          reference=p.reference, document_state=p.document_state)
            for p in sales.list_historical_payments(company_id, date_from, date_to)
        ]


class ReceivablesPaymentSource:
    def list_payments(self, company_id: UUID, date_from: date | None, date_to: date | None) -> list[SourcePayment]:
        return [
            SourcePayment('SERVICE', p.id, p.amount, p.method, p.payment_date, document_ref=p.document_ref,
                          receipt_number=p.receipt_number, reference=p.reference, recorded_by=p.recorded_by,
                          recorded_by_name=p.recorded_by_name, document_state=p.document_state)
            for p in receivables.list_historical_payments(company_id, date_from, date_to)
        ]


class DjangoRegularizationLedger:
    def entries_by_origin(self, company_id: UUID, origin_kind: str, ids: list[UUID]) -> dict[UUID, Entry]:
        return DjangoEntryRepository(company_id).by_origin(origin_kind, ids)

    @staticmethod
    def _key(company_id: UUID) -> int:
        return int.from_bytes(hashlib.sha256(company_id.bytes).digest()[:4], 'big', signed=True)

    def try_lock(self, company_id: UUID) -> bool:
        """Bloqueo de sesión por empresa: una sola regularización a la vez."""
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_try_advisory_lock(%s, %s)', [_LOCK_NAMESPACE, self._key(company_id)])
            return bool(cursor.fetchone()[0])

    def unlock(self, company_id: UUID) -> None:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_unlock(%s, %s)', [_LOCK_NAMESPACE, self._key(company_id)])

    def create(self, company_id: UUID, item: Item, regularized_at: datetime, executed_by: str) -> bool:
        payment = item.payment
        try:
            with transaction.atomic():
                result = accounting.record_entry(company_id, accounting.EntryInput(
                    account_id=item.account_id, currency=item.currency, amount=payment.amount,
                    payment_date=payment.payment_date, method=payment.method, origin_kind=payment.origin_kind,
                    origin_id=payment.id, origin_document_ref=payment.document_ref,
                    receipt_number=payment.receipt_number, recorded_by=payment.recorded_by,
                    recorded_by_name=payment.recorded_by_name, regularized_at=regularized_at,
                    regularized_by_name=executed_by))
        except accounting.EntryValidationError as exc:
            raise LedgerRejected(next((m[0] for m in exc.errors.values() if m), 'datos no válidos.')) from exc
        except accounting.EntryConflict as exc:
            raise LedgerRejected(str(exc)) from exc
        return result.created
