"""Asiento de partida doble (CONT-02): cabecera + líneas, confirmado e inmutable. Dominio puro: sin Django."""
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from .account import AccountValidationError
from .catalog import CURRENCIES

MAX_DIGITS = 12
DECIMAL_PLACES = 2
DESCRIPTION_MAX = 200
REASON_MAX = 200
MEMO_MAX = 200
ORIGIN_KIND_MAX = 30
MANUAL = 'MANUAL'
AUTOMATIC = 'AUTOMATIC'
SOURCES = (MANUAL, AUTOMATIC)
ZERO = Decimal('0.00')
_QUANT = Decimal(1).scaleb(-DECIMAL_PLACES)

# Códigos de `JournalConflict`.
ORIGIN_CONFLICT = 'origin_conflict'
ORIGIN_IN_LEGACY_LEDGER = 'origin_in_legacy_ledger'


class JournalValidationError(AccountValidationError):
    """Datos inválidos de un asiento; `errors` mapea campo -> mensajes."""


class JournalEntryNotFound(Exception):
    pass


class JournalConflict(Exception):
    """El asiento choca con otro (mismo evento con datos distintos, u origen ya contabilizado en el libro anterior)."""

    def __init__(self, code: str, message: str, fields: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.fields = fields or []


def _fail(name: str, message: str):
    raise JournalValidationError({name: [message]})


def _money(name: str, value: object) -> Decimal:
    """Importe exacto (≥ 0) con a lo sumo 2 decimales; `None` equivale a cero. Nunca `float`."""
    if value is None:
        return ZERO
    if isinstance(value, (float, bool)):
        _fail(name, 'El importe debe ser un decimal, no un número de punto flotante.')
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        _fail(name, 'El importe no es válido.')
    if not amount.is_finite():
        _fail(name, 'El importe no es válido.')
    if amount < 0:
        _fail(name, 'El importe no puede ser negativo.')
    if amount != amount.quantize(_QUANT):
        _fail(name, f'El importe admite como máximo {DECIMAL_PLACES} decimales.')
    if amount >= Decimal(10) ** (MAX_DIGITS - DECIMAL_PLACES):
        _fail(name, 'El importe es demasiado grande.')
    return amount.quantize(_QUANT)


def _text(name: str, value: object, maximum: int, required: bool) -> str:
    if value is None or value == '':
        value = ''
    if not isinstance(value, str):
        _fail(name, 'El texto no es válido.')
    value = value.strip()
    if required and not value:
        _fail(name, 'Es obligatorio.')
    if len(value) > maximum:
        _fail(name, f'No puede superar {maximum} caracteres.')
    return value


@dataclass(frozen=True)
class JournalLineInput:
    """Línea tal como la entrega quien contabiliza: la cuenta y el importe del lado usado."""
    account_id: UUID
    debit: Decimal | None = None
    credit: Decimal | None = None
    memo: str = ''


@dataclass(frozen=True)
class JournalLine:
    """Una línea: una cuenta con Debe o Haber (uno solo, positivo)."""
    account_id: UUID
    debit: Decimal = ZERO
    credit: Decimal = ZERO
    memo: str = ''
    position: int = 0

    @classmethod
    def create(cls, account_id: object, debit: object, credit: object, memo: object, position: int) -> 'JournalLine':
        if not isinstance(account_id, UUID):
            _fail('lines', f'La línea {position + 1} requiere una cuenta.')
        debit_amount = _money(f'lines[{position}].debit', debit)
        credit_amount = _money(f'lines[{position}].credit', credit)
        if debit_amount > 0 and credit_amount > 0:
            _fail('lines', f'La línea {position + 1} no puede tener Debe y Haber a la vez.')
        if debit_amount == 0 and credit_amount == 0:
            _fail('lines', f'La línea {position + 1} requiere un importe en Debe o en Haber.')
        return cls(account_id, debit_amount, credit_amount, _text('lines', memo, MEMO_MAX, False), position)

    def inverted(self) -> 'JournalLine':
        return replace(self, debit=self.credit, credit=self.debit)


@dataclass(frozen=True)
class JournalEntry:
    """Asiento confirmado. Una corrección es otro asiento (`reverse`); nunca se edita ni se borra."""
    id: UUID
    accounting_date: date
    description: str
    source: str
    currency: str
    lines: tuple[JournalLine, ...]
    origin_kind: str | None = None
    origin_id: UUID | None = None
    period_id: UUID | None = None
    created_by: int | None = None
    created_by_name: str = ''
    created_at: datetime | None = None
    reverses_id: UUID | None = None
    reversal_reason: str = ''
    reversed_by_id: UUID | None = field(default=None, compare=False)  # lo informa el repositorio al leer

    @property
    def total_debit(self) -> Decimal:
        return sum((line.debit for line in self.lines), ZERO)

    @property
    def total_credit(self) -> Decimal:
        return sum((line.credit for line in self.lines), ZERO)

    @property
    def is_reversal(self) -> bool:
        return self.reverses_id is not None

    @classmethod
    def post(cls, *, accounting_date: object, description: object, currency: object, lines: object,
             origin_kind: object = None, origin_id: object = None, created_by: int | None = None,
             created_by_name: str = '') -> 'JournalEntry':
        """Valida y crea un asiento: manual (sin origen) o automático (con `origin_kind` y `origin_id`)."""
        if not isinstance(accounting_date, date) or isinstance(accounting_date, datetime):
            _fail('accounting_date', 'La fecha contable no es válida.')
        if currency not in CURRENCIES:
            _fail('currency', f'La moneda debe ser una de: {", ".join(CURRENCIES)}.')
        if (origin_kind in (None, '')) != (origin_id is None):
            _fail('origin_id', 'El origen automático requiere tipo e identificador de evento.')
        kind = None
        if origin_id is not None:
            if not isinstance(origin_id, UUID):
                _fail('origin_id', 'El identificador del evento no es válido.')
            kind = _text('origin_kind', origin_kind, ORIGIN_KIND_MAX, True)
        entry = cls(
            id=uuid4(), accounting_date=accounting_date,
            description=_text('description', description, DESCRIPTION_MAX, True),
            source=AUTOMATIC if origin_id is not None else MANUAL, currency=currency,
            lines=build_lines(lines), origin_kind=kind, origin_id=origin_id, created_by=created_by,
            created_by_name=created_by_name or '')
        entry._ensure_balanced()
        return entry

    def _ensure_balanced(self) -> None:
        if len({line.account_id for line in self.lines}) < 2:
            _fail('lines', 'El asiento requiere al menos dos cuentas distintas.')
        if self.total_debit != self.total_credit:
            _fail('lines', f'El asiento no cuadra: Debe {self.total_debit} y Haber {self.total_credit}.')
        if self.total_debit <= 0:
            _fail('lines', 'El total del asiento debe ser mayor que cero.')

    def with_period(self, period_id: UUID) -> 'JournalEntry':
        return replace(self, period_id=period_id)

    def reverse(self, reversal_date: object, reason: object, created_by: int | None = None,
                created_by_name: str = '') -> 'JournalEntry':
        """Contra-asiento completo: mismas cuentas con Debe/Haber invertidos, vinculado a este (que no cambia)."""
        if self.is_reversal:
            _fail('entry', 'Una reversión no se puede revertir.')
        if not isinstance(reversal_date, date) or isinstance(reversal_date, datetime):
            _fail('accounting_date', 'La fecha de la reversión no es válida.')
        text = _text('reason', reason, REASON_MAX, True)
        return JournalEntry(
            id=uuid4(), accounting_date=reversal_date, description=f'Reversión: {self.description}'[:DESCRIPTION_MAX],
            source=self.source, currency=self.currency, lines=tuple(line.inverted() for line in self.lines),
            created_by=created_by, created_by_name=created_by_name or '', reverses_id=self.id, reversal_reason=text)

    def differences(self, other: 'JournalEntry') -> list[str]:
        """Campos de negocio que difieren de otro asiento del mismo evento (para detectar reintentos incompatibles)."""
        def lines(entry: 'JournalEntry'):
            return sorted((str(line.account_id), line.debit, line.credit) for line in entry.lines)

        found = [name for name in ('accounting_date', 'description', 'currency')
                 if getattr(self, name) != getattr(other, name)]
        return found + (['lines'] if lines(self) != lines(other) else [])


def build_lines(lines: object) -> tuple[JournalLine, ...]:
    if not isinstance(lines, (list, tuple)) or len(lines) < 2:
        _fail('lines', 'El asiento requiere al menos dos líneas.')
    return tuple(JournalLine.create(getattr(raw, 'account_id', None), getattr(raw, 'debit', None),
                                    getattr(raw, 'credit', None), getattr(raw, 'memo', ''), index)
                 for index, raw in enumerate(lines))
