from datetime import datetime
from typing import Protocol
from uuid import UUID

from modules.costing.domain.costing import CostOrigin, CostState, Valuation, value_entry, value_exit
from modules.costing.domain.exceptions import MovementValuationRejected
from shared.stock_valuation import MovementToValue


class ValuationStorePort(Protocol):
    def cutoff_at(self) -> datetime | None: ...

    def lock_state(self, product_id: UUID) -> CostState: ...

    def save_state(self, product_id: UUID, state: CostState) -> None: ...

    def last_occurred_at(self, product_id: UUID) -> datetime | None: ...

    def by_movement(self, movement_id: UUID): ...

    def has_later(self, product_id: UUID, after_id: int) -> bool: ...

    def add(self, **kwargs) -> None: ...


RETROACTIVE_MESSAGE = ('No se puede registrar un movimiento con fecha anterior a otro ya valorado del producto: '
                       'obligaría a recalcular costos de consumos. Use la fecha actual.')
REVERSAL_LATER_MESSAGE = ('No se puede revertir: hay movimientos posteriores de este producto que ya consumieron '
                          'su costo y habría que revalorarlos.')
REVERSAL_UNVALUED_MESSAGE = ('No se puede revertir un movimiento anterior a la adopción de la valoración porque '
                             'no tiene un costo registrado; registre un ajuste positivo con su valor.')


class ValueMovement:
    """Valora un movimiento de una empresa con inventario valorado: promedio móvil, snapshot y estado (AC-01..09).

    Se ejecuta dentro de la transacción del movimiento; toma la fila de costo del producto (`lock_state`).
    """

    def __init__(self, store: ValuationStorePort):
        self.store = store

    def execute(self, movement: MovementToValue) -> Valuation | None:
        cutoff = self.store.cutoff_at()
        if cutoff is None:
            return None
        state = self.store.lock_state(movement.product_id)
        self._check_not_retroactive(movement, cutoff)
        if movement.reverses_id is not None:
            valuation = self._reversal(movement, state)
        elif movement.kind == 'in':
            valuation = self._entry(movement, state)
        else:
            valuation = value_exit(state, movement.quantity)
        self.store.add(
            movement_id=movement.movement_id, product_id=movement.product_id, valuation=valuation,
            source_type=movement.source_type, source_id=movement.source_id,
            reverses_movement_id=movement.reverses_id, occurred_at=movement.occurred_at)
        self.store.save_state(movement.product_id, valuation.state_after)
        return valuation

    def _check_not_retroactive(self, movement: MovementToValue, cutoff: datetime) -> None:
        last = self.store.last_occurred_at(movement.product_id)
        if movement.occurred_at < cutoff or (last is not None and movement.occurred_at < last):
            raise MovementValuationRejected('valuation_blocked', RETROACTIVE_MESSAGE)

    @staticmethod
    def _entry(movement: MovementToValue, state: CostState) -> Valuation:
        value = movement.value
        if value is None:
            return value_entry(state, movement.quantity, cost_origin=CostOrigin.MANUAL_ADJUSTMENT.value)
        return value_entry(
            state, movement.quantity, unit_cost=value.unit_cost, total_value=value.total_value,
            declared_zero=value.declared_zero, cost_origin=value.cost_origin)

    def _reversal(self, movement: MovementToValue, state: CostState) -> Valuation:
        original = self.store.by_movement(movement.reverses_id)
        if movement.kind == 'out':  # revierte una entrada
            if original is None:
                return value_exit(state, movement.quantity)  # anterior al corte: sale al promedio vigente
            if self.store.has_later(movement.product_id, original.id):
                raise MovementValuationRejected('valuation_blocked', REVERSAL_LATER_MESSAGE)
            return value_exit(state, movement.quantity, exact_value=original.valuation.value,
                              cost_origin=CostOrigin.REVERSAL_SNAPSHOT.value)
        if original is None:  # revierte una salida sin costo conocido
            raise MovementValuationRejected('valuation_blocked', REVERSAL_UNVALUED_MESSAGE)
        return value_entry(state, movement.quantity, total_value=original.valuation.value,
                           declared_zero=original.valuation.value == 0,
                           cost_origin=CostOrigin.REVERSAL_SNAPSHOT.value)
