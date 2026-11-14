"""Agregado Obligation (puro: sin Django). Dinero siempre en `Decimal` a dos decimales."""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from uuid import UUID, uuid4

from shared.domain.commitment import ACCEPTED, CommitmentSnapshot

ZERO = Decimal('0.00')
_CENTS = Decimal('0.01')
MAX_AMOUNT = Decimal('9999999999.99')
MAX_REFERENCE = 100
MAX_ALLOCATIONS = 200
KINDS = ('quotation', 'dental')
PENDING, PARTIAL, PAID = 'pending', 'partial', 'paid'


class PaymentMethod(str, Enum):
    """Mismos métodos que Ventas; todos se consideran activos."""
    CASH = 'CASH'
    QR = 'QR'
    BANK_TRANSFER = 'BANK_TRANSFER'
    CARD = 'CARD'
    OTHER = 'OTHER'


class ObligationValidationError(Exception):
    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(errors)


class ObligationStateError(Exception):
    """Operación no permitida para el estado actual (se traduce a 409); `code` opcional para el cliente."""

    def __init__(self, message: str = '', code: str = ''):
        super().__init__(message)
        self.code = code


class CommitmentNotFound(Exception):
    pass


def money(value: Decimal) -> Decimal:
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


def _is_money(value: object) -> bool:
    return isinstance(value, Decimal) and value.is_finite() and value == value.quantize(_CENTS)


@dataclass(frozen=True)
class Allocation:
    lineage_id: UUID
    line_id: UUID
    description: str
    amount: Decimal


@dataclass(frozen=True)
class Payment:
    id: UUID
    receipt_number: str
    amount: Decimal
    payment_method: PaymentMethod
    payment_date: date
    reference: str
    allocations: tuple[Allocation, ...]
    recorded_by: int | None = None
    recorded_by_name: str = ''
    created_at: datetime | None = None
    idempotency_key: UUID | None = None


@dataclass(frozen=True)
class StatementLine:
    line_id: UUID
    lineage_id: UUID
    description: str
    piece: str
    decision: str
    proposed: Decimal
    accepted: Decimal
    paid: Decimal
    balance: Decimal
    collectible: bool


@dataclass(frozen=True)
class Statement:
    """Vista derivada: nada de esto se guarda ni se asigna desde fuera (INV-05)."""
    lines: tuple[StatementLine, ...]
    proposed: Decimal
    accepted: Decimal
    pending: Decimal
    rejected: Decimal
    paid: Decimal
    balance: Decimal
    payment_status: str


def _status(accepted: Decimal, paid: Decimal) -> str:
    if accepted > 0 and paid >= accepted:
        return PAID
    return PARTIAL if paid > 0 else PENDING


def build_statement(snapshot: CommitmentSnapshot, payments: list[Payment]) -> Statement:
    paid_by_lineage: dict[UUID, Decimal] = {}
    for payment in payments:
        for allocation in payment.allocations:
            paid_by_lineage[allocation.lineage_id] = (
                paid_by_lineage.get(allocation.lineage_id, ZERO) + allocation.amount)
    lines = []
    totals = {'accepted': ZERO, 'pending': ZERO, 'rejected': ZERO}
    for line in snapshot.lines:
        accepted = line.amount if line.decision == ACCEPTED else ZERO
        paid = paid_by_lineage.get(line.lineage_id, ZERO)
        balance = max(accepted - paid, ZERO)
        totals[line.decision if line.decision in totals else 'pending'] += line.amount
        lines.append(StatementLine(line.line_id, line.lineage_id, line.description, line.piece, line.decision,
                                   line.amount, accepted, paid, balance, snapshot.collectible and balance > 0))
    accepted_total = money(totals['accepted'])
    paid_total = money(sum(paid_by_lineage.values(), ZERO))
    return Statement(tuple(lines), money(sum((l.amount for l in snapshot.lines), ZERO)), accepted_total,
                     money(totals['pending']), money(totals['rejected']), paid_total,
                     money(max(accepted_total - paid_total, ZERO)), _status(accepted_total, paid_total))


@dataclass
class Obligation:
    id: UUID
    source_kind: str
    source_number: str
    customer_id: UUID
    customer_name: str
    payments: list[Payment] = field(default_factory=list)
    created_at: datetime | None = None

    @classmethod
    def open(cls, snapshot: CommitmentSnapshot) -> 'Obligation':
        return cls(uuid4(), snapshot.kind, snapshot.number, snapshot.customer_id, snapshot.customer_name)

    def statement(self, snapshot: CommitmentSnapshot) -> Statement:
        return build_statement(snapshot, self.payments)

    def register_payment(self, snapshot: CommitmentSnapshot, *, amount: object, payment_method: object,
                         payment_date: date | None, reference: object, allocations: list[tuple[UUID, Decimal]],
                         today: date, receipt_number: str, recorded_by: int | None = None,
                         recorded_by_name: str = '', idempotency_key: UUID | None = None,
                         now: datetime | None = None) -> Payment:
        if not snapshot.collectible:
            raise ObligationStateError('Solo se puede cobrar una proforma presentada vigente.')
        errors: dict = {}
        if not _is_money(amount) or amount <= 0 or amount > MAX_AMOUNT:
            errors['amount'] = ['Ingresa un monto mayor que cero con dos decimales.']
        try:
            method = PaymentMethod(payment_method)
        except ValueError:
            method = None
            errors['payment_method'] = ['Elige un método de pago válido.']
        when = today if payment_date is None else payment_date
        if when > today:
            errors['payment_date'] = ['La fecha del pago no puede ser futura.']
        text = (reference or '').strip() if isinstance(reference, str) or reference is None else None
        if text is None or len(text) > MAX_REFERENCE:
            errors['reference'] = [f'Máximo {MAX_REFERENCE} caracteres.']
        built = self._allocations(snapshot, allocations, errors)
        if not errors and sum((a.amount for a in built), ZERO) != amount:
            errors['allocations'] = ['La suma de las imputaciones debe ser igual al monto del pago.']
        if errors:
            raise ObligationValidationError(errors)
        payment = Payment(uuid4(), receipt_number, amount, method, when, text, tuple(built), recorded_by,
                          recorded_by_name, now, idempotency_key)
        self.payments.append(payment)
        return payment

    def _allocations(self, snapshot: CommitmentSnapshot, allocations, errors: dict) -> list[Allocation]:
        if not allocations:
            errors['allocations'] = ['Distribuye el pago en al menos un tratamiento.']
            return []
        if len(allocations) > MAX_ALLOCATIONS:
            errors['allocations'] = [f'Máximo {MAX_ALLOCATIONS} imputaciones.']
            return []
        ids = [line_id for line_id, _ in allocations]
        if len(set(ids)) != len(ids):
            errors['allocations'] = ['Hay tratamientos repetidos.']
            return []
        by_id = {line.line_id: line for line in build_statement(snapshot, self.payments).lines}
        built = []
        for line_id, value in allocations:
            line = by_id.get(line_id)
            if line is None:
                errors['allocations'] = ['Alguna línea no pertenece a la proforma.']
            elif line.decision != ACCEPTED:
                errors['allocations'] = [f'«{line.description}» no está aceptado: no se puede cobrar.']
            elif not _is_money(value) or value <= 0:
                errors['allocations'] = [f'Imputa un importe mayor que cero en «{line.description}».']
            elif value > line.balance:
                errors['allocations'] = [f'La imputación a «{line.description}» supera su saldo ({line.balance}).']
            else:
                built.append(Allocation(line.lineage_id, line.line_id, line.description, value))
                continue
            return []
        return built
