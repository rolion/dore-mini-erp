from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, Sequence
from uuid import UUID

from django.utils import timezone

from modules.inventory.domain.exceptions import LotNotFound, MovementConflict, MovementValidationError
from modules.inventory.domain.lot import LotNumber, LotPosition, StockLot
from modules.inventory.domain.movement import MovementKind, MovementSource, StockMovement, parse_quantity
from modules.inventory.domain.repositories import (
    LotFilters,
    StockLotRepository,
    StockMovementRepository,
    WarehouseRepository,
)

from .movement_ports import InventoryPolicy, ProductDirectory
from .movement_use_cases import RecordMovement


class LotNumbering(Protocol):
    """Asigna el siguiente número de la serie de lotes del período fiscal que contiene `lot_date`.

    Debe ejecutarse dentro de la transacción de la creación (el número se revierte con ella). Lanza
    `LotNumberingRejected` con `fiscal_period_missing` o `fiscal_period_closed` si no hay período abierto.
    """

    def next_number(self, lot_date: date) -> LotNumber: ...


@dataclass(frozen=True)
class CreatedLot:
    lot: StockLot
    movement: StockMovement
    created: bool


class CreateLot:
    """Crea un lote en refrigeración con su entrada inicial, todo en una transacción (AC-01..AC-04).

    Idempotente por el origen del movimiento (`source`): repetir devuelve el mismo lote sin gastar número. La entrada
    la registra `RecordMovement` (mismas validaciones de producto, unidad y almacén que cualquier movimiento).
    """

    def __init__(self, stock: StockMovementRepository, lots: StockLotRepository, warehouses: WarehouseRepository,
                 products: ProductDirectory, numbering: LotNumbering, policy: InventoryPolicy | None = None):
        self.stock = stock
        self.lots = lots
        self.warehouses = warehouses
        self.numbering = numbering
        self.recorder = RecordMovement(stock, warehouses, products, policy, lots)

    def execute(self, *, product_id: UUID, warehouse_id: UUID, quantity: object, source: MovementSource,
                user_id: UUID | None, user_name: str, reference: str = '',
                occurred_at: datetime | None = None) -> CreatedLot:
        parsed = parse_quantity(quantity)
        when = occurred_at or timezone.now()
        lot_date = timezone.localtime(when).date()
        with self.stock.locked(warehouse_id):
            existing = self._existing(source, product_id, warehouse_id)
            if existing is not None:
                if existing.quantity != parsed:
                    raise MovementConflict(
                        'source_operation_mismatch',
                        'Esa operación de origen ya registró un lote con otra cantidad.')
                return CreatedLot(self.lots.get(existing.lot_id), existing, False)
            warehouse = self.warehouses.get(warehouse_id)
            if warehouse is None:
                raise MovementValidationError({'warehouse_id': ['El almacén no existe.']})
            lot = self.lots.insert(StockLot.create(
                product_id=product_id, warehouse_id=warehouse_id, lot_date=lot_date,
                number=self.numbering.next_number(lot_date)))
            # Si algo falla desde aquí (producto inválido, almacén inactivo…), la transacción revierte lote y número.
            movement, _ = self.recorder.execute(
                product_id=product_id, warehouse_id=warehouse_id, kind=MovementKind.IN, quantity=parsed,
                user_id=user_id, user_name=user_name, reference=reference or lot.code, source=source,
                occurred_at=when, lot_id=lot.id)
            return CreatedLot(lot, movement, True)

    def _existing(self, source: MovementSource, product_id: UUID, warehouse_id: UUID) -> StockMovement | None:
        for movement in self.stock.find_by_source_id(source.type, source.id):
            if (movement.lot_id is not None and movement.product_id == product_id
                    and movement.warehouse_id == warehouse_id and movement.source == source):
                return movement
        return None


class ReleaseLot:
    """Pasa un lote de «en refrigeración» a «liberado» (AC-06). Repetirlo no cambia nada.

    La regla de cuánto debe refrigerarse antes de liberar es de Producción; Inventario solo cambia el estado.
    """

    def __init__(self, stock: StockMovementRepository, lots: StockLotRepository):
        self.stock = stock
        self.lots = lots

    def execute(self, lot_id: UUID, *, user_id: UUID | None, user_name: str) -> tuple[LotPosition, bool]:
        lot = self.lots.get(lot_id)
        if lot is None:
            raise LotNotFound(lot_id)
        with self.stock.locked(lot.warehouse_id):  # el mismo bloqueo que serializa las salidas del lote
            lot = self.lots.get(lot_id)
            changed = lot.release(now=timezone.now(), user_id=user_id, user_name=user_name.strip())
            if changed:
                self.lots.save_release(lot)
            return self.lots.get_position(lot_id), changed


class ListLots:
    def __init__(self, lots: StockLotRepository):
        self.lots = lots

    def execute(self, filters: LotFilters) -> Sequence[LotPosition]:
        return self.lots.list(filters)


class GetLot:
    def __init__(self, lots: StockLotRepository):
        self.lots = lots

    def execute(self, lot_id: UUID) -> LotPosition:
        position = self.lots.get_position(lot_id)
        if position is None:
            raise LotNotFound(lot_id)
        return position
