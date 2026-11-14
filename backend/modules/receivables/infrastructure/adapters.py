"""Puente de Cobros hacia las fachadas públicas de las fuentes del compromiso (Cotizaciones y Odontología)."""
from collections.abc import Iterable
from uuid import UUID

from modules.accounting import services as accounting
from modules.dentistry import services as dental
from modules.quotations import services as quotations
from modules.receivables.domain.obligation import ObligationStateError, Payment
from shared import module_gate
from shared.domain.commitment import CommitmentSnapshot

ACCOUNTING_MODULE = 'accounting'
PAYMENT_CURRENCY = 'BOB'


class CommitmentSource:
    """Lee, bloquea y marca líneas de un tipo de proforma; el módulo concreto se elige por `kind`."""

    def __init__(self, facade, company_id: UUID):
        self._facade = facade
        self.company_id = company_id

    def get(self, number: str) -> CommitmentSnapshot | None:
        return self._facade.get_commitment(self.company_id, number)

    def get_many(self, numbers: Iterable[str]) -> dict[str, CommitmentSnapshot]:
        return self._facade.get_commitments(self.company_id, numbers)

    def lock(self, number: str) -> CommitmentSnapshot | None:
        return self._facade.lock_commitment(self.company_id, number)

    def mark_collected(self, line_ids: Iterable[UUID]) -> None:
        self._facade.mark_lines_collected(self.company_id, line_ids)


_FACADES = {quotations.KIND: quotations, dental.KIND: dental}


def source_for(kind: str, company_id: UUID) -> CommitmentSource | None:
    facade = _FACADES.get(kind)
    return CommitmentSource(facade, company_id) if facade else None


class PaymentLedgerAdapter:
    """Cada pago crea su entrada en el libro de Contabilidad (origen `SERVICE`) si el módulo está habilitado."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is None:
            self._available = module_gate.is_enabled(self.company_id, ACCOUNTING_MODULE)
        return self._available

    def record(self, kind: str, number: str, payment: Payment, actor_id: int | None, actor_name: str) -> None:
        method = payment.payment_method.value
        account = accounting.resolve_account(self.company_id, method)
        if account is None:
            raise ObligationStateError(
                'El método de pago no tiene una cuenta destino activa. Configúrala en Contabilidad → Cuentas y '
                'Métodos de pago e inténtalo de nuevo.', 'payment_method_without_account')
        try:
            accounting.record_entry(self.company_id, accounting.EntryInput(
                account_id=account.account_id, currency=PAYMENT_CURRENCY, amount=payment.amount,
                payment_date=payment.payment_date, method=method, origin_kind='SERVICE', origin_id=payment.id,
                origin_document_ref=number, receipt_number=payment.receipt_number, recorded_by=actor_id,
                recorded_by_name=actor_name))
        except accounting.EntryValidationError as exc:
            detail = next((m[0] for m in exc.errors.values() if m), 'datos no válidos.')
            raise ObligationStateError('Contabilidad rechazó la entrada del cobro: ' + detail, 'ledger_rejected') from exc
        except accounting.EntryConflict as exc:
            raise ObligationStateError(str(exc), 'ledger_conflict') from exc
