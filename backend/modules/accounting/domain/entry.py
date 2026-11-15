from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from .account import AccountValidationError
from .catalog import CURRENCIES, METHOD_CODES, ORIGIN_KINDS

MAX_DIGITS = 12
DECIMAL_PLACES = 2


class EntryValidationError(AccountValidationError):
    """Datos inválidos de una entrada; `errors` mapea campo -> mensajes."""


class EntryNotFound(Exception):
    pass


class EntryConflict(Exception):
    """Ya existe una entrada para ese origen con datos distintos; `fields` lista los campos que difieren."""

    def __init__(self, fields: list[str]):
        super().__init__(f'La entrada del origen ya existe con otros datos: {", ".join(fields)}.')
        self.fields = fields


class EntryContractError(Exception):
    """El contrato se usó mal (p. ej. fuera de la transacción del pago)."""


def _fail(field: str, message: str):
    raise EntryValidationError({field: [message]})


def _amount(value: object) -> Decimal:
    if isinstance(value, float) or isinstance(value, bool):
        _fail('amount', 'El monto debe ser un decimal, no un número de punto flotante.')
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        _fail('amount', 'El monto no es válido.')
    if not amount.is_finite() or amount <= 0:
        _fail('amount', 'El monto debe ser mayor que cero.')
    if amount != amount.quantize(Decimal(1).scaleb(-DECIMAL_PLACES)):
        _fail('amount', f'El monto admite como máximo {DECIMAL_PLACES} decimales.')
    if amount >= Decimal(10) ** (MAX_DIGITS - DECIMAL_PLACES):
        _fail('amount', 'El monto es demasiado grande.')
    return amount.quantize(Decimal(1).scaleb(-DECIMAL_PLACES))


def _choice(field: str, value: object, options: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in options:
        _fail(field, f'Valor no válido; use uno de: {", ".join(options)}.')
    return value


@dataclass(frozen=True)
class Entry:
    """Dinero efectivamente recibido por un pago de origen. Inmutable: no se corrige ni se elimina."""
    id: UUID
    account_id: UUID
    currency: str
    amount: Decimal
    payment_date: date
    method: str
    origin_kind: str
    origin_id: UUID
    origin_document_ref: str = ''
    receipt_number: str = ''
    recorded_by: int | None = None
    recorded_by_name: str = ''
    created_at: datetime | None = None
    # Solo las entradas creadas por regularización de pagos históricos: cuándo y quién la ejecutó (no el autor del cobro).
    regularized_at: datetime | None = None
    regularized_by_name: str = ''

    @classmethod
    def record(cls, *, account_id: UUID, currency: object, amount: object, payment_date: object, method: object,
               origin_kind: object, origin_id: UUID, origin_document_ref: str = '', receipt_number: str = '',
               recorded_by: int | None = None, recorded_by_name: str = '',
               regularized_at: datetime | None = None, regularized_by_name: str = '') -> 'Entry':
        if not isinstance(payment_date, date) or isinstance(payment_date, datetime):
            _fail('payment_date', 'La fecha del pago no es válida.')
        return cls(
            id=uuid4(), account_id=account_id, currency=_choice('currency', currency, CURRENCIES),
            amount=_amount(amount), payment_date=payment_date, method=_choice('method', method, METHOD_CODES),
            origin_kind=_choice('origin_kind', origin_kind, ORIGIN_KINDS), origin_id=origin_id,
            origin_document_ref=origin_document_ref or '', receipt_number=receipt_number or '',
            recorded_by=recorded_by, recorded_by_name=recorded_by_name or '',
            regularized_at=regularized_at, regularized_by_name=regularized_by_name or '')

    def differences(self, other: 'Entry') -> list[str]:
        """Campos de negocio que difieren de otra entrada del mismo origen (para detectar reintentos incompatibles)."""
        fields = ('account_id', 'currency', 'amount', 'payment_date', 'method', 'origin_document_ref',
                  'receipt_number')
        return [name for name in fields if getattr(self, name) != getattr(other, name)]
