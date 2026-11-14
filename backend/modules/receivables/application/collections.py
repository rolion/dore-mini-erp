import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from modules.receivables.domain.obligation import (
    CommitmentNotFound, Obligation, ObligationStateError, Payment, Statement, build_statement,
)
from shared.domain.commitment import CommitmentSnapshot


@dataclass(frozen=True)
class PaymentInput:
    idempotency_key: UUID
    amount: Decimal
    payment_method: str
    payment_date: date | None
    reference: str
    allocations: tuple[tuple[UUID, Decimal], ...]


@dataclass(frozen=True)
class CommitmentView:
    snapshot: CommitmentSnapshot
    obligation: Obligation | None
    statement: Statement


@dataclass(frozen=True)
class PaymentResult:
    view: CommitmentView
    payment: Payment
    replayed: bool


class PaymentLedger(Protocol):
    """Puerto del libro de entradas: lo implementa un adaptador; puede no estar disponible."""

    def is_available(self) -> bool: ...

    def record(self, kind: str, number: str, payment: Payment, actor_id: int | None, actor_name: str) -> None: ...


def _digest(kind: str, number: str, data: PaymentInput) -> str:
    body = [kind, number, str(data.amount), data.payment_method, str(data.payment_date), data.reference.strip(),
            sorted((str(line_id), str(value)) for line_id, value in data.allocations)]
    return hashlib.sha256(json.dumps(body).encode()).hexdigest()


class CollectionService:
    """Casos de uso de Cobros: consultar un compromiso, registrar pagos y listar obligaciones."""

    def __init__(self, repository, source_for: Callable, *, today: Callable[[], date], now: Callable[[], datetime],
                 user_id: int | None = None, user_name: str = '',
                 ledger: PaymentLedger | None = None):
        self.repository = repository
        self.source_for = source_for
        self.today, self.now = today, now
        self.user_id, self.user_name = user_id, user_name
        self.ledger = ledger

    def _source(self, kind: str):
        source = self.source_for(kind)
        if source is None:
            raise CommitmentNotFound()
        return source

    def get(self, kind: str, number: str) -> CommitmentView:
        snapshot = self._source(kind).get(number)
        if snapshot is None:
            raise CommitmentNotFound()
        obligation = self.repository.find(kind, number)
        return CommitmentView(snapshot, obligation, build_statement(snapshot, obligation.payments if obligation else []))

    def register_payment(self, kind: str, number: str, data: PaymentInput) -> PaymentResult:
        """Debe ejecutarse dentro de una transacción. Orden de bloqueo fijo: obligación → proforma (ADR)."""
        source = self._source(kind)
        digest = _digest(kind, number, data)
        replay = self._replay(kind, number, data.idempotency_key, digest)
        if replay:
            return replay
        snapshot = source.get(number)
        if snapshot is None:
            raise CommitmentNotFound()
        obligation = self.repository.lock_or_create(Obligation.open(snapshot))
        replay = self._replay(kind, number, data.idempotency_key, digest)  # una igual pudo ganar la carrera
        if replay:
            return replay
        snapshot = source.lock(number)
        if snapshot is None:
            raise CommitmentNotFound()
        payment = obligation.register_payment(
            snapshot, amount=data.amount, payment_method=data.payment_method, payment_date=data.payment_date,
            reference=data.reference, allocations=list(data.allocations), today=self.today(),
            receipt_number=self.repository.next_receipt(), recorded_by=self.user_id,
            recorded_by_name=self.user_name, idempotency_key=data.idempotency_key, now=self.now())
        self.repository.add_payment(obligation, payment, digest)
        if self.ledger is not None and self.ledger.is_available():
            self.ledger.record(kind, number, payment, self.user_id, self.user_name)
        source.mark_collected(a.line_id for a in payment.allocations)
        view = CommitmentView(snapshot, obligation, build_statement(snapshot, obligation.payments))
        return PaymentResult(view, payment, False)

    def _replay(self, kind: str, number: str, key: UUID, digest: str) -> PaymentResult | None:
        """INV-06: misma clave y mismo contenido → el pago ya registrado; misma clave con otro contenido → 409."""
        found = self.repository.find_payment_by_key(key)
        if found is None:
            return None
        row, stored_hash = found
        if stored_hash != digest or row.obligation.source_kind != kind or row.obligation.source_number != number:
            raise ObligationStateError('La clave de la operación ya se usó con otros datos.')
        view = self.get(kind, number)
        payment = next(p for p in view.obligation.payments if p.id == row.id)
        return PaymentResult(view, payment, True)

    def list(self, *, customer_id: UUID | None = None, date_from: date | None = None, date_to: date | None = None,
             status: str = '') -> list[CommitmentView]:
        obligations = self.repository.search(customer_id=customer_id, date_from=date_from, date_to=date_to)
        views = []
        for kind in {o.source_kind for o in obligations}:
            source = self._source(kind)
            snapshots = source.get_many(o.source_number for o in obligations if o.source_kind == kind)
            for obligation in obligations:
                snapshot = snapshots.get(obligation.source_number) if obligation.source_kind == kind else None
                if snapshot is not None:
                    views.append(CommitmentView(snapshot, obligation, build_statement(snapshot, obligation.payments)))
        if status:
            views = [v for v in views if v.statement.payment_status == status]
        return sorted(views, key=lambda v: (v.obligation.created_at, v.obligation.id), reverse=True)
