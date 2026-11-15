from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from .catalog import ACCOUNT_KINDS, CURRENCIES, FLOW_CURRENCY

NAME_MAX_LENGTH = 80


class AccountValidationError(Exception):
    """Datos inválidos; `errors` mapea campo -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class AccountNotFound(Exception):
    pass


class MethodNotFound(Exception):
    pass


class AccountConflict(Exception):
    """La acción choca con el estado actual; `methods` lista los métodos activos afectados."""

    def __init__(self, code: str, message: str, methods: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.methods = methods or []


def validate_name(name: object) -> str:
    if not isinstance(name, str) or not name.strip():
        raise AccountValidationError({'name': ['El nombre es obligatorio.']})
    name = name.strip()
    if len(name) > NAME_MAX_LENGTH:
        raise AccountValidationError({'name': [f'El nombre no puede superar {NAME_MAX_LENGTH} caracteres.']})
    return name


def validate_currency(currency: object) -> str:
    if not isinstance(currency, str) or currency.strip().upper() not in CURRENCIES:
        raise AccountValidationError({'currency': [f'La moneda debe ser una de: {", ".join(CURRENCIES)}.']})
    return currency.strip().upper()


OPENING_MAX = Decimal(10) ** 10
ZERO = Decimal('0.00')


def validate_opening_balance(value: object) -> Decimal:
    """Saldo de apertura: decimal ≥ 0 con a lo sumo 2 decimales (nunca float)."""
    if isinstance(value, (float, bool)):
        raise AccountValidationError({'opening_balance': ['El saldo de apertura debe ser un decimal.']})
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise AccountValidationError({'opening_balance': ['El saldo de apertura no es válido.']}) from None
    if not amount.is_finite() or amount < 0:
        raise AccountValidationError({'opening_balance': ['El saldo de apertura no puede ser negativo.']})
    if amount != amount.quantize(Decimal('0.01')):
        raise AccountValidationError({'opening_balance': ['El saldo de apertura admite como máximo 2 decimales.']})
    if amount >= OPENING_MAX:
        raise AccountValidationError({'opening_balance': ['El saldo de apertura es demasiado grande.']})
    return amount.quantize(Decimal('0.01'))


def validate_kind(kind: object) -> str:
    if not isinstance(kind, str) or kind.strip().upper() not in ACCOUNT_KINDS:
        raise AccountValidationError({'kind': [f'El tipo debe ser uno de: {", ".join(ACCOUNT_KINDS)}.']})
    return kind.strip().upper()


@dataclass
class Account:
    id: UUID
    name: str
    currency: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Caja/Banco/Billetera; nulo solo en cuentas anteriores a su introducción. No restringe la dirección del dinero.
    kind: str | None = None
    # Monto de la cuenta a la fecha de corte; cambia solo mientras la cuenta no tiene movimientos.
    opening_balance: Decimal = ZERO

    @classmethod
    def create(cls, name: object, currency: object, kind: object = None,
               opening_balance: object = None) -> 'Account':
        return cls(id=uuid4(), name=validate_name(name), currency=validate_currency(currency),
                   kind=validate_kind(kind) if kind is not None else None,
                   opening_balance=validate_opening_balance(opening_balance) if opening_balance is not None else ZERO)

    def set_opening_balance(self, value: object) -> None:
        self.opening_balance = validate_opening_balance(value)

    def rename(self, name: object) -> None:
        self.name = validate_name(name)

    def change_kind(self, kind: object) -> None:
        self.kind = validate_kind(kind)

    def change_currency(self, currency: object) -> None:
        self.currency = validate_currency(currency)

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False

    @property
    def can_receive(self) -> bool:
        """Puede ser destino de un método activo: activa y en la moneda de los flujos."""
        return self.is_active and self.currency == FLOW_CURRENCY


@dataclass
class MethodMapping:
    """Destino vigente de un método de la empresa. `account_id` nulo = método sin destino todavía."""
    code: str
    is_active: bool = True
    account_id: UUID | None = None

    def configure(self, account: Account | None, is_active: bool) -> None:
        if is_active and account is not None and not account.can_receive:
            reason = ('La cuenta está inactiva.' if not account.is_active
                      else f'La cuenta debe estar en {FLOW_CURRENCY} para recibir cobros.')
            raise AccountValidationError({'account_id': [reason]})
        self.account_id = account.id if account else None
        self.is_active = is_active

    def is_complete(self, accounts: dict[UUID, Account]) -> bool:
        """Un método inactivo no necesita destino; uno activo exige una cuenta que pueda recibir."""
        if not self.is_active:
            return True
        account = accounts.get(self.account_id) if self.account_id else None
        return account is not None and account.can_receive
