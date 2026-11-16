"""Caso de uso del diagnóstico de transición (CONT-07, Etapa 1): solo lectura, siempre acotado a una empresa."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from modules.accounting.domain.regularization import SourcePayment
from modules.accounting.domain.transition import (
    BEFORE_CUTOFF,
    CONVERTIBLE,
    HISTORICAL,
    PENDING,
    EntryFact,
    SourceFact,
    TransitionMapping,
    classify_entry,
    classify_opening,
)

VERIFIABLE_ORIGINS = ('PRODUCT', 'SERVICE')  # accounting solo lee Ventas y Cobros (no puede importar Gastos ni Compras)
NO_ENTRY = 'sin_entrada'


@dataclass(frozen=True)
class AccountFact:
    id: UUID
    kind: str | None
    opening_balance: Decimal
    is_active: bool
    has_entries: bool


class TransitionReader(Protocol):
    def company_ids(self) -> list[UUID]: ...

    def cutoff(self, company_id: UUID) -> date | None: ...

    def accounts(self, company_id: UUID) -> list[AccountFact]: ...

    def entries(self, company_id: UUID) -> list[EntryFact]: ...


class PaymentSource(Protocol):
    def list_payments(self, company_id: UUID, date_from: date | None, date_to: date | None) -> list[SourcePayment]: ...


def _money(value: Decimal) -> str:
    return f'{value:.2f}'


def _bump(bucket: dict, key, amount: Decimal) -> None:
    row = bucket.setdefault(key, [0, Decimal('0.00')])
    row[0] += 1
    row[1] += amount


def _table(bucket: dict) -> dict:
    return {key: {'count': count, 'amount': _money(total)} for key, (count, total) in sorted(bucket.items())}


class DiagnoseTransition:
    def __init__(self, reader: TransitionReader, sources: dict[str, PaymentSource]):
        self.reader = reader
        self.sources = sources

    def company_ids(self) -> list[UUID]:
        return self.reader.company_ids()

    def diagnose(self, company_id: UUID, mapping: TransitionMapping | None = None) -> dict:
        mapping = mapping or TransitionMapping()
        cutoff = self.reader.cutoff(company_id)
        accounts = self.reader.accounts(company_id)
        entries = self.reader.entries(company_id)
        known = {a.id for a in accounts}
        payments = {kind: {p.id: p for p in source.list_payments(company_id, None, None)}
                    for kind, source in self.sources.items()}

        by_shape: dict = {}
        states: dict = {}
        reasons: dict = {}
        details: list[dict] = []
        for entry in entries:
            _bump(by_shape, f'{entry.direction}/{entry.operation}/{entry.origin_kind}', entry.amount)
            payment = payments.get(entry.origin_kind, {}).get(entry.origin_id)
            verdict = classify_entry(entry, SourceFact(payment.amount) if payment else None,
                                     entry.origin_kind in VERIFIABLE_ORIGINS, cutoff, known, mapping)
            _bump(states, verdict.state, entry.amount)
            if verdict.reason:
                reasons[verdict.reason] = reasons.get(verdict.reason, 0) + 1
            if verdict.state == PENDING:
                details.append({'entry_id': str(entry.id), 'origin': entry.origin_kind,
                                'origin_id': str(entry.origin_id), 'operation': entry.operation,
                                'payment_date': entry.payment_date.isoformat(),
                                'amount': _money(entry.amount), 'reason': verdict.reason})

        entered = {(e.origin_kind, e.origin_id) for e in entries}
        without_entry: dict = {}
        for kind, rows in payments.items():
            for payment in rows.values():
                if (kind, payment.id) in entered:
                    continue
                reason = BEFORE_CUTOFF if cutoff and payment.payment_date < cutoff else NO_ENTRY
                _bump(without_entry, f'{kind}/{reason}', payment.amount)

        openings = []
        for account in accounts:
            opening = classify_opening(account.opening_balance, account.id, cutoff, mapping)
            if opening:
                openings.append({'account_id': str(account.id), 'amount': _money(account.opening_balance),
                                 'state': opening.state, 'reason': opening.reason})
        return {
            'company_id': str(company_id),
            'cutoff_date': cutoff.isoformat() if cutoff else None,
            'blocked_without_cutoff': bool(entries) and cutoff is None,
            'accounts': {
                'total': len(accounts), 'active': sum(a.is_active for a in accounts),
                'with_kind': sum(a.kind is not None for a in accounts),
                'without_kind': sum(a.kind is None for a in accounts),
                'with_entries': sum(a.has_entries for a in accounts),
                'opening_total': _money(sum((a.opening_balance for a in accounts), Decimal('0.00')))},
            'entries': {
                'total': len(entries), 'amount': _money(sum((e.amount for e in entries), Decimal('0.00'))),
                'regularized': sum(e.regularized for e in entries),
                'without_classification': sum(e.classification_id is None for e in entries),
                'by_shape': _table(by_shape)},
            'states': {state: _table(states).get(state, {'count': 0, 'amount': '0.00'}) for state in
                       (CONVERTIBLE, HISTORICAL, PENDING)},
            'reasons': dict(sorted(reasons.items())),
            'source_without_entry': _table(without_entry),
            'openings': openings,
            'details': details,
        }
