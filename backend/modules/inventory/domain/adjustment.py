import re
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from .exceptions import AdjustmentValidationError, NoDifference
from .movement import MovementKind, MovementStatus

SOURCE_TYPE = 'inventory_adjustment'
REASON_MAX_LENGTH = 200
COUNTED_DECIMALS = Decimal('0.001')
COUNTED_MAX = Decimal('99999999999.999')
BALANCE_DECIMALS = Decimal('0.0001')
# Solo texto decimal simple: sin signo, exponente ni dígitos no ASCII (igual que la interfaz).
_PLAIN_DECIMAL = re.compile(r'\d+(\.\d+)?', re.ASCII)


def _error(field_name: str, message: str) -> AdjustmentValidationError:
    return AdjustmentValidationError({field_name: [message]})


def validate_counted_quantity(value: object) -> Decimal:
    """Cantidad contada: decimal no negativo con hasta 3 decimales. Nunca `float` (ni `bool`)."""
    name = 'counted_quantity'
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise _error(name, 'La cantidad contada debe ser un número decimal.')
    text = value.strip() if isinstance(value, str) else None
    if text is not None:
        if text.startswith('-') and _PLAIN_DECIMAL.fullmatch(text[1:]):
            raise _error(name, 'La cantidad contada no puede ser negativa.')
        if not _PLAIN_DECIMAL.fullmatch(text):
            raise _error(name, 'La cantidad contada debe ser un número decimal.')
    try:
        quantity = Decimal(text if text is not None else value)
    except InvalidOperation:
        raise _error(name, 'La cantidad contada debe ser un número decimal.') from None
    if not quantity.is_finite():
        raise _error(name, 'La cantidad contada debe ser un número decimal.')
    if quantity < 0:
        raise _error(name, 'La cantidad contada no puede ser negativa.')
    # El tope va antes de `quantize`: un exponente enorme lanzaría `InvalidOperation` (500) en vez de un 400.
    if quantity > COUNTED_MAX:
        raise _error(name, f'La cantidad contada no puede superar {COUNTED_MAX}.')
    if quantity != quantity.quantize(COUNTED_DECIMALS):
        raise _error(name, 'La cantidad contada admite como máximo 3 decimales.')
    return quantity.quantize(COUNTED_DECIMALS)


def validate_expected_balance(value: object) -> Decimal:
    """Saldo que la persona vio al contar (puede ser negativo)."""
    name = 'expected_system_quantity'
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise _error(name, 'El saldo del sistema debe ser un número decimal.')
    try:
        balance = Decimal(value.strip() if isinstance(value, str) else value)
    except InvalidOperation:
        raise _error(name, 'El saldo del sistema debe ser un número decimal.') from None
    if not balance.is_finite() or abs(balance) > COUNTED_MAX or balance != balance.quantize(BALANCE_DECIMALS):
        raise _error(name, 'El saldo del sistema debe ser un decimal de hasta 4 decimales.')
    return balance.quantize(BALANCE_DECIMALS)


def validate_reason(value: object) -> str:
    reason = value.strip() if isinstance(value, str) else ''
    if not reason:
        raise _error('reason', 'El motivo es obligatorio.')
    if len(reason) > REASON_MAX_LENGTH:
        raise _error('reason', f'El motivo no puede superar {REASON_MAX_LENGTH} caracteres.')
    return reason


def reference_for(adjustment_id: UUID) -> str:
    return f'AJ-{adjustment_id.hex[:8].upper()}'


@dataclass(frozen=True)
class StockAdjustment:
    """Corrección de un saldo tras un conteo (INV-01..03): inmutable, ligada al movimiento que genera."""

    id: UUID
    product_id: UUID
    warehouse_id: UUID
    system_quantity: Decimal
    counted_quantity: Decimal
    reason: str
    user_id: UUID | None
    user_name: str
    reference: str
    movement_id: UUID | None = None
    created_at: datetime | None = None
    status: MovementStatus = MovementStatus.CONFIRMED

    @classmethod
    def create(cls, *, adjustment_id: UUID, product_id: UUID, warehouse_id: UUID, system_quantity: Decimal,
               counted_quantity: Decimal, reason: str, user_id: UUID | None, user_name: str) -> 'StockAdjustment':
        adjustment = cls(
            id=adjustment_id, product_id=product_id, warehouse_id=warehouse_id, system_quantity=system_quantity,
            counted_quantity=counted_quantity, reason=reason, user_id=user_id, user_name=user_name,
            reference=reference_for(adjustment_id))
        if adjustment.difference == 0:
            raise NoDifference()
        return adjustment

    @property
    def difference(self) -> Decimal:
        return self.counted_quantity - self.system_quantity

    @property
    def kind(self) -> MovementKind:
        return MovementKind.IN if self.difference > 0 else MovementKind.OUT

    def with_movement(self, movement_id: UUID) -> 'StockAdjustment':
        return replace(self, movement_id=movement_id)
