from datetime import datetime
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from django.utils import timezone

from modules.inventory.domain.exceptions import MovementConflict, MovementNotFound, MovementValidationError
from modules.inventory.domain.movement import MovementKind, MovementSource, StockMovement
from modules.inventory.domain.repositories import (
    MovementFilters,
    StockMovementRepository,
    WarehouseRepository,
)

from .movement_ports import ProductDirectory


class RecordMovement:
    """Registra una entrada o salida. Repetir la misma operación de origen devuelve el movimiento ya registrado."""

    def __init__(self, repository: StockMovementRepository, warehouses: WarehouseRepository,
                 products: ProductDirectory):
        self.repository = repository
        self.warehouses = warehouses
        self.products = products

    def execute(self, *, product_id: UUID, warehouse_id: UUID, kind: MovementKind | str, quantity: object,
                user_id: UUID | None, user_name: str, reference: str = '', reason: str = '',
                source: MovementSource | None = None, occurred_at: datetime | None = None,
                allow_negative: bool = False) -> tuple[StockMovement, bool]:
        movement = StockMovement.record(
            product_id=product_id, warehouse_id=warehouse_id, kind=MovementKind(kind), quantity=quantity,
            occurred_at=occurred_at or timezone.now(), user_id=user_id, user_name=user_name,
            reference=reference, reason=reason, source=source)
        product = self.products.get_products([product_id]).get(product_id)
        if product is None:
            raise MovementValidationError({'product_id': ['El producto no existe.']})
        if not product.tracks_stock:
            raise MovementValidationError({'product_id': ['El producto no controla stock.']})
        if not product.allows_fractions and movement.quantity != movement.quantity.to_integral_value():
            raise MovementValidationError({'quantity': ['La unidad del producto no admite fracciones.']})

        with self.repository.locked(warehouse_id):
            # Se valida bajo el bloqueo: desactivar un almacén toma el mismo bloqueo.
            warehouse = self.warehouses.get(warehouse_id)
            if warehouse is None:
                raise MovementValidationError({'warehouse_id': ['El almacén no existe.']})
            if not warehouse.active:
                raise MovementValidationError({'warehouse_id': ['El almacén está inactivo.']})
            existing = self.repository.find_by_source(movement)
            if existing is not None:  # reintento de la misma operación de origen
                if existing.quantity != movement.quantity:
                    raise MovementConflict(
                        'source_operation_mismatch',
                        'Esa operación de origen ya registró un movimiento con otra cantidad.')
                return existing, False
            self._check_balance(movement, allow_negative)
            return self.repository.insert(movement), True

    def _check_balance(self, movement: StockMovement, allow_negative: bool) -> None:
        if movement.kind is MovementKind.OUT and not allow_negative:
            available = self.repository.balance(movement.product_id, movement.warehouse_id)
            if available < movement.quantity:
                raise MovementConflict('insufficient_stock', 'No hay saldo suficiente para registrar la salida.')


class ReverseMovement:
    def __init__(self, repository: StockMovementRepository):
        self.repository = repository

    def execute(self, movement_id: UUID, *, user_id: UUID | None, user_name: str, reason: str = '',
                allow_negative: bool = False) -> StockMovement:
        original = self.repository.get(movement_id)
        if original is None:
            raise MovementNotFound(movement_id)
        with self.repository.locked(original.warehouse_id):
            original = self.repository.get(movement_id)  # estado vigente, ya bajo el bloqueo
            counter = original.reverse(
                occurred_at=timezone.now(), user_id=user_id, user_name=user_name, reason=reason)
            if counter.kind is MovementKind.OUT and not allow_negative:
                if self.repository.balance(counter.product_id, counter.warehouse_id) < counter.quantity:
                    raise MovementConflict(
                        'insufficient_stock', 'No hay saldo suficiente para revertir esta entrada.')
            created = self.repository.insert(counter)
            self.repository.mark_reversed(original.id)
            return created


class GetBalance:
    def __init__(self, repository: StockMovementRepository):
        self.repository = repository

    def execute(self, product_id: UUID, warehouse_id: UUID) -> Decimal:
        return self.repository.balance(product_id, warehouse_id)


class ListMovements:
    def __init__(self, repository: StockMovementRepository):
        self.repository = repository

    def execute(self, filters: MovementFilters) -> Sequence[StockMovement]:
        return self.repository.list(filters)


class GetMovement:
    def __init__(self, repository: StockMovementRepository):
        self.repository = repository

    def execute(self, movement_id: UUID) -> StockMovement:
        movement = self.repository.get(movement_id)
        if movement is None:
            raise MovementNotFound(movement_id)
        return movement
