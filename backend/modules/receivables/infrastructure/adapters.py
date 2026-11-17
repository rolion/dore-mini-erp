"""Puente de Cobros hacia las fachadas públicas de las fuentes del compromiso (Cotizaciones y Odontología)."""
from collections.abc import Iterable
from contextlib import contextmanager
from decimal import Decimal
from uuid import UUID

from modules.accounting import services as accounting
from modules.dentistry import services as dental
from modules.quotations import services as quotations
from modules.receivables.domain.obligation import (
    Obligation, ObligationStateError, Payment, RenderedService, split_payment,
)
from shared import module_gate
from shared.domain.commitment import CommitmentSnapshot

ACCOUNTING_MODULE = 'accounting'
PAYMENT_CURRENCY = 'BOB'
SERVICE_ADVANCE, SERVICE_RECOGNITION, SERVICE_PAYMENT = 'SERVICE_ADVANCE', 'SERVICE_RECOGNITION', 'SERVICE_PAYMENT'


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


class ServicePostingAdapter:
    """Contabiliza Cobros en Contabilidad (solo por su fachada `services`), si el módulo está habilitado.

    Cobros a tratamientos sin prestar → anticipo de cliente; tratamiento prestado → reconocimiento del ingreso
    (aplicando los anticipos); cobros a tratamientos prestados → contra Cuentas por cobrar. Lo que no tiene cobertura
    de partida doble sigue en el libro anterior (origen `SERVICE`). Cada porción de un cobro sigue un único camino.
    """

    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is None:
            self._available = module_gate.is_enabled(self.company_id, ACCOUNTING_MODULE)
        return self._available

    def _covers(self, on) -> bool:
        return accounting.coverage_status(self.company_id, on).covered

    def record_payment(self, kind: str, number: str, obligation: Obligation, payment: Payment,
                       actor_id: int | None, actor_name: str) -> None:
        recognized_ids = accounting.automatic_entry_origins(
            self.company_id, SERVICE_RECOGNITION, [s.id for s in obligation.rendered])
        portions = split_payment(payment, {s.lineage_id for s in obligation.rendered},
                                 {s.lineage_id for s in obligation.rendered if s.id in recognized_ids})
        legacy = portions.rendered_unposted
        if portions.settlement > 0:  # Debe método / Haber Cuentas por cobrar
            posted = self._post(SERVICE_PAYMENT, number, payment, portions.settlement, actor_id, actor_name)
            if not posted:
                raise ObligationStateError(
                    'La fecha del cobro no tiene cobertura contable; usa una fecha posterior al corte de '
                    'Contabilidad.', 'payment_date_not_covered')
        if portions.advance > 0:
            if self._covers(payment.payment_date):  # Debe método / Haber Anticipos de clientes
                self._post(SERVICE_ADVANCE, number, payment, portions.advance, actor_id, actor_name)
            else:
                legacy += portions.advance
        if legacy > 0:
            self._record_in_legacy_ledger(number, payment, legacy, actor_id, actor_name)

    def _post(self, event: str, number: str, payment: Payment, amount: Decimal, actor_id, actor_name) -> bool:
        with _posting_errors():
            posted = accounting.post_automatic_entry(
                self.company_id, event, payment.id, payment.payment_date, f'Cobro del servicio {number}', amount,
                method=payment.payment_method.value, created_by=actor_id, created_by_name=actor_name)
        return posted.posted

    def recognize(self, kind: str, number: str, obligation: Obligation, service: RenderedService,
                  actor_id: int | None, actor_name: str) -> None:
        applied = obligation.applied_to(service.lineage_id)
        if not self._covers(service.service_date):
            if applied > 0:
                raise ObligationStateError(
                    'El tratamiento tiene anticipos contabilizados y la fecha de prestación no tiene cobertura '
                    'contable; usa una fecha de prestación posterior al corte de Contabilidad.',
                    'service_date_not_covered')
            return  # prestado antes de la cobertura: sin asiento (los cobros posteriores van al libro anterior)
        payments = [p for p in obligation.payments if any(a.lineage_id == service.lineage_id for a in p.allocations)]
        advanced = accounting.automatic_entry_origins(self.company_id, SERVICE_ADVANCE, [p.id for p in payments])
        if any(p.id not in advanced for p in payments):
            raise ObligationStateError(
                'El tratamiento tiene cobros registrados sin asiento contable (hechos antes de la cobertura de '
                'Contabilidad) y no puede marcarse como prestado hasta definir su tratamiento.',
                'service_has_unposted_payments')
        with _posting_errors():
            accounting.post_automatic_entry(
                self.company_id, SERVICE_RECOGNITION, service.id, service.service_date,
                f'Servicio prestado {number}: {service.description}', service.amount, advance_applied=applied,
                created_by=actor_id, created_by_name=actor_name)

    def _record_in_legacy_ledger(self, number: str, payment: Payment, amount: Decimal, actor_id, actor_name) -> None:
        """Libro anterior (origen `SERVICE`) para lo cobrado sin cobertura de partida doble, como antes de SRV-01."""
        method = payment.payment_method.value
        account = accounting.resolve_account(self.company_id, method)
        if account is None:
            raise ObligationStateError(
                'El método de pago no tiene una cuenta destino activa. Configúrala en Contabilidad → Cuentas y '
                'Métodos de pago e inténtalo de nuevo.', 'payment_method_without_account')
        try:
            accounting.record_entry(self.company_id, accounting.EntryInput(
                account_id=account.account_id, currency=PAYMENT_CURRENCY, amount=amount,
                payment_date=payment.payment_date, method=method, origin_kind='SERVICE', origin_id=payment.id,
                origin_document_ref=number, receipt_number=payment.receipt_number, recorded_by=actor_id,
                recorded_by_name=actor_name))
        except accounting.EntryValidationError as exc:
            detail = next((m[0] for m in exc.errors.values() if m), 'datos no válidos.')
            raise ObligationStateError('Contabilidad rechazó la entrada del cobro: ' + detail,
                                       'ledger_rejected') from exc
        except accounting.EntryConflict as exc:
            raise ObligationStateError(str(exc), 'ledger_conflict') from exc


@contextmanager
def _posting_errors():
    """Traduce los rechazos del motor y de la configuración a errores de Cobros (409 accionables)."""
    try:
        yield
    except accounting.PostingConfigurationMissing as exc:
        issues = [{'code': i.code, 'role': i.role, 'subject': i.subject, 'message': i.message, 'params': i.params}
                  for i in exc.issues]
        raise ObligationStateError('; '.join(i['message'] for i in issues), 'posting_configuration_missing',
                                   {'issues': issues}) from exc
    except (accounting.FiscalPeriodClosed, accounting.DateOutsideFiscalPeriod) as exc:
        raise ObligationStateError(str(exc), 'fiscal_period_unavailable') from exc
    except accounting.JournalValidationError as exc:
        detail = next((m[0] for m in exc.errors.values() if m), 'datos no válidos.')
        raise ObligationStateError('Contabilidad rechazó el asiento: ' + detail, 'ledger_rejected') from exc
    except accounting.JournalConflict as exc:
        raise ObligationStateError(str(exc), 'ledger_conflict') from exc
