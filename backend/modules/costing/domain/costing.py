"""Costo promedio ponderado móvil por producto (puro: sin Django).

El estado corriente (`CostState`) y el snapshot de cada movimiento (`Valuation`) se calculan aquí; el snapshot es
de solo lectura una vez guardado y nunca se recalcula.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from .exceptions import MovementValuationRejected
from .valuation import MONEY_STEP, TOTAL_MAX, UNIT_COST_STEP, _parse_decimal, compute_unit_cost

ZERO = Decimal('0')
ZERO_MONEY = Decimal('0.00')
REQUIRED_MESSAGE = 'Indique el valor total de la entrada: el inventario está valorado.'


class CostOrigin(str, Enum):
    PURCHASE_PRICE = 'purchase_price'
    MANUAL_ADJUSTMENT = 'manual_adjustment'
    AVERAGE_AT_EXIT = 'average_at_exit'
    REVERSAL_SNAPSHOT = 'reversal_snapshot'


def round_money(amount: Decimal) -> Decimal:
    return amount.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CostState:
    """Cantidad y valor corrientes del producto en toda la empresa."""

    quantity: Decimal = ZERO
    total_value: Decimal = ZERO_MONEY

    @property
    def average(self) -> Decimal:
        return compute_unit_cost(self.total_value, self.quantity) if self.quantity > 0 else ZERO.quantize(UNIT_COST_STEP)


@dataclass(frozen=True)
class Valuation:
    """Snapshot de un movimiento: costo aplicado, valor y el promedio antes y después."""

    kind: str
    quantity: Decimal
    unit_cost: Decimal
    value: Decimal
    average_before: Decimal
    average_after: Decimal
    quantity_after: Decimal
    total_value_after: Decimal
    cost_origin: str

    @property
    def state_after(self) -> CostState:
        return CostState(self.quantity_after, self.total_value_after)


def _bad(message: str, code: str = 'valuation_invalid') -> MovementValuationRejected:
    return MovementValuationRejected(code, message)


def _money(raw: object, label: str) -> Decimal:
    value = _parse_decimal(raw)
    if value is None or value != value.quantize(MONEY_STEP):
        raise _bad(f'{label} debe ser un importe en BOB no negativo con hasta 2 decimales.')
    if value > TOTAL_MAX:
        raise _bad(f'{label} no puede superar {TOTAL_MAX}.')
    return value.quantize(MONEY_STEP)


def value_entry(state: CostState, quantity: Decimal, *, unit_cost: Decimal | None = None,
                total_value: Decimal | None = None, declared_zero: bool = False,
                cost_origin: str) -> Valuation:
    """Entrada: con `unit_cost` (precio de compra) o con `total_value` explícito (ajuste positivo)."""
    if unit_cost is not None:
        if unit_cost < 0:
            raise _bad('El costo unitario no puede ser negativo.')
        cost = unit_cost.quantize(UNIT_COST_STEP, rounding=ROUND_HALF_UP)
        value = round_money(quantity * cost)
        if value > TOTAL_MAX:
            raise _bad(f'El valor no puede superar {TOTAL_MAX}.')
    else:
        if total_value is None:
            raise MovementValuationRejected('valuation_required', REQUIRED_MESSAGE)
        value = _money(total_value, 'El valor total')
        if declared_zero and value != 0:
            raise _bad('Un costo cero declarado no admite un valor distinto de cero.')
        if value == 0 and not declared_zero:
            raise _bad('Un costo cero debe declararse explícitamente.')
        cost = compute_unit_cost(value, quantity)
    after = CostState(state.quantity + quantity, state.total_value + value)
    return Valuation('in', quantity, cost, value, state.average, after.average, after.quantity, after.total_value,
                     cost_origin)


def value_exit(state: CostState, quantity: Decimal, *, exact_value: Decimal | None = None,
               cost_origin: str = CostOrigin.AVERAGE_AT_EXIT.value) -> Valuation:
    """Salida al promedio vigente; la que vacía el producto toma todo el valor (sin residuo de centavos)."""
    if quantity > state.quantity:
        raise MovementValuationRejected(
            'valuation_blocked',
            'La salida supera la cantidad valorada del producto; revise las existencias antes de continuar.')
    if exact_value is not None and exact_value > state.total_value:
        raise MovementValuationRejected(
            'valuation_blocked', 'El valor a retirar supera el valor vigente del producto.')
    average = state.average
    if exact_value is not None:
        value = exact_value
    elif quantity == state.quantity:
        value = state.total_value
    else:
        value = min(round_money(quantity * average), state.total_value)
    cost = compute_unit_cost(value, quantity) if exact_value is not None else average
    after = CostState(state.quantity - quantity, state.total_value - value)
    return Valuation('out', quantity, cost, value, average, after.average, after.quantity, after.total_value,
                     cost_origin)
