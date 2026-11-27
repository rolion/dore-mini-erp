"""Costo promedio móvil ponderado (puro: sin Django).

El costo de una salida es cantidad × costo promedio vigente del producto; las salidas no cambian el promedio.
Las recepciones lo actualizan. Dinero siempre `Decimal`: costo unitario a 6 decimales y total de línea a 2
(`ROUND_HALF_UP`).
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from uuid import UUID

from .valuation import MONEY_STEP, UNIT_COST_STEP

ZERO = Decimal('0')


class CostKind(str, Enum):
    IN = 'in'  # recepción: actualiza el promedio
    OUT = 'out'  # salida valorizada al promedio vigente
    IN_REVERSAL = 'in_reversal'  # reversa de una recepción, al costo original
    OUT_REVERSAL = 'out_reversal'  # reversa (devolución) de una salida, al costo registrado al vender


def weighted_average(previous_balance: Decimal, previous_average: Decimal | None, quantity: Decimal,
                     unit_cost: Decimal) -> Decimal:
    """Nuevo promedio tras recibir `quantity` a `unit_cost`.

    Sin saldo previo positivo o sin promedio conocido el promedio es el costo de la recepción.
    """
    if previous_balance <= 0 or previous_average is None:
        return unit_cost.quantize(UNIT_COST_STEP, rounding=ROUND_HALF_UP)
    total = previous_balance * previous_average + quantity * unit_cost
    return (total / (previous_balance + quantity)).quantize(UNIT_COST_STEP, rounding=ROUND_HALF_UP)


def line_cost(quantity: Decimal, unit_cost: Decimal) -> Decimal:
    """Valor de una línea: cantidad × costo unitario, a 2 decimales."""
    return (quantity * unit_cost).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CostEvent:
    """Hecho inmutable del ledger de costo; único por `(tipo, origen, producto)`."""

    kind: CostKind
    source_type: str
    source_id: str
    product_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    average_after: Decimal
    occurred_at: datetime
    reverses_id: int | None = None
    id: int | None = None

    @classmethod
    def receipt(cls, source_type: str, source_id: str, product_id: UUID, quantity: Decimal, unit_cost: Decimal,
                average_after: Decimal, occurred_at: datetime) -> 'CostEvent':
        return cls(CostKind.IN, source_type, source_id, product_id, quantity, unit_cost,
                   line_cost(quantity, unit_cost), average_after, occurred_at)

    @classmethod
    def output(cls, source_type: str, source_id: str, product_id: UUID, quantity: Decimal, average: Decimal,
               occurred_at: datetime) -> 'CostEvent':
        return cls(CostKind.OUT, source_type, source_id, product_id, quantity, average,
                   line_cost(quantity, average), average, occurred_at)

    def reversal(self, average_after: Decimal, occurred_at: datetime) -> 'CostEvent':
        """Contra-evento de una recepción: conserva el costo original y el vínculo."""
        return CostEvent(CostKind.IN_REVERSAL, self.source_type, self.source_id, self.product_id, self.quantity,
                         self.unit_cost, self.total_cost, average_after, occurred_at, reverses_id=self.id)

    def output_reversal(self, occurred_at: datetime) -> 'CostEvent':
        """Contra-evento de una salida (devolución): conserva el costo de venta; el promedio no cambia."""
        return CostEvent(CostKind.OUT_REVERSAL, self.source_type, self.source_id, self.product_id, self.quantity,
                         self.unit_cost, self.total_cost, self.average_after, occurred_at, reverses_id=self.id)


class CostUnavailable(Exception):
    """No hay costo para valorizar la salida: Costeo sin adoptar o producto sin promedio. Nunca se inventa un valor."""

    code = 'inventory_cost_unavailable'
    NOT_ADOPTED = 'not_adopted'
    NO_AVERAGE = 'no_average'

    def __init__(self, reason: str, product_ids: list[UUID] | None = None):
        if reason == self.NOT_ADOPTED:
            message = 'Costeo no tiene una valoración inicial adoptada: no hay costo para las existencias.'
        else:
            message = 'Hay productos sin costo promedio: no se puede valorizar la salida.'
        super().__init__(message)
        self.reason = reason
        self.product_ids = product_ids or []
