from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from django.utils import timezone

from modules.inventory.domain.exceptions import (
    InsufficientStock,
    MovementConflict,
    MovementNotFound,
    MovementValidationError,
    Shortage,
)
from modules.inventory.domain.movement import (
    MovementKind,
    MovementSource,
    MovementStatus,
    StockMovement,
    reversal_block,
)
from modules.inventory.domain.repositories import (
    MovementFilters,
    StockMovementRepository,
    WarehouseRepository,
)

from .movement_ports import BlockNegativeStock, InventoryPolicy, ProductDirectory, apply_valuation


class RecordMovement:
    """Registra una entrada o salida. Repetir la misma operación de origen devuelve el movimiento ya registrado."""

    def __init__(self, repository: StockMovementRepository, warehouses: WarehouseRepository,
                 products: ProductDirectory, policy: InventoryPolicy | None = None):
        self.repository = repository
        self.warehouses = warehouses
        self.products = products
        self.policy = policy or BlockNegativeStock()

    def execute(self, *, product_id: UUID, warehouse_id: UUID, kind: MovementKind | str, quantity: object,
                user_id: UUID | None, user_name: str, reference: str = '', reason: str = '',
                source: MovementSource | None = None, occurred_at: datetime | None = None,
                valuation: object | None = None) -> tuple[StockMovement, bool]:
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
            self._check_balance(movement)
            apply_valuation(self.policy, movement, valuation)
            return self.repository.insert(movement), True

    def _check_balance(self, movement: StockMovement) -> None:
        # La política se lee ya bajo el bloqueo del almacén: la misma sección crítica valida y registra.
        if movement.kind is MovementKind.OUT and not self.policy.allow_negative_stock():
            available = self.repository.balance(movement.product_id, movement.warehouse_id)
            if available < movement.quantity:
                raise InsufficientStock(
                    'No hay saldo suficiente para registrar la salida.', product_id=movement.product_id,
                    warehouse_id=movement.warehouse_id, requested=movement.quantity, available=available)


@dataclass(frozen=True)
class OutputLine:
    """Una salida de un documento de origen: producto, cantidad y clave de línea (parte de la identidad)."""

    product_id: UUID
    quantity: object
    line: str = ''


class RecordOutputs:
    """Registra las salidas de un documento (varias líneas) en un almacén, todas o ninguna.

    Un solo bloqueo del almacén cubre la validación de todas las líneas, la política de negativo y las inserciones.
    Las líneas ya registradas por la misma operación de origen se devuelven con `created=False` (reintento).
    """

    def __init__(self, repository: StockMovementRepository, warehouses: WarehouseRepository,
                 products: ProductDirectory, policy: InventoryPolicy | None = None):
        self.repository = repository
        self.warehouses = warehouses
        self.products = products
        self.policy = policy or BlockNegativeStock()

    def execute(self, *, warehouse_id: UUID, lines: Sequence[OutputLine], source_type: str, source_id: str,
                user_id: UUID | None, user_name: str, reference: str = '',
                occurred_at: datetime | None = None) -> list[tuple[StockMovement, bool]]:
        when = occurred_at or timezone.now()
        movements = [
            StockMovement.record(
                product_id=line.product_id, warehouse_id=warehouse_id, kind=MovementKind.OUT,
                quantity=line.quantity, occurred_at=when, user_id=user_id, user_name=user_name,
                reference=reference, source=MovementSource(source_type, source_id, line.line))
            for line in lines]
        found = self.products.get_products([m.product_id for m in movements])
        for movement in movements:
            product = found.get(movement.product_id)
            if product is None:
                raise MovementValidationError({'product_id': ['El producto no existe.']})
            if not product.tracks_stock:
                raise MovementValidationError({'product_id': ['El producto no controla stock.']})
            if not product.allows_fractions and movement.quantity != movement.quantity.to_integral_value():
                raise MovementValidationError({'quantity': ['La unidad del producto no admite fracciones.']})

        with self.repository.locked(warehouse_id):
            warehouse = self.warehouses.get(warehouse_id)
            if warehouse is None:
                raise MovementValidationError({'warehouse_id': ['El almacén no existe.']})
            if not warehouse.active:
                raise MovementValidationError({'warehouse_id': ['El almacén está inactivo.']})
            results: list[tuple[StockMovement, bool] | None] = []
            pending: list[tuple[int, StockMovement]] = []
            for index, movement in enumerate(movements):
                existing = self.repository.find_by_source(movement)
                if existing is None:
                    results.append(None)
                    pending.append((index, movement))
                elif existing.quantity != movement.quantity:
                    raise MovementConflict(
                        'source_operation_mismatch',
                        'Esa operación de origen ya registró un movimiento con otra cantidad.')
                else:
                    results.append((existing, False))
            self._check_balances(warehouse_id, [m for _, m in pending])
            for index, movement in sorted(pending, key=lambda item: str(item[1].product_id)):
                apply_valuation(self.policy, movement)
                results[index] = (self.repository.insert(movement), True)
            return results  # type: ignore[return-value]

    def _check_balances(self, warehouse_id: UUID, pending: list[StockMovement]) -> None:
        # La política se lee ya bajo el bloqueo del almacén, igual que en RecordMovement.
        if not pending or self.policy.allow_negative_stock():
            return
        balances = self.repository.balances_for(warehouse_id, [m.product_id for m in pending])
        shortages: list[Shortage] = []
        for movement in pending:
            available = balances.get(movement.product_id, Decimal('0'))
            if available < movement.quantity:
                shortages.append(Shortage(movement.product_id, movement.quantity, available))
        if shortages:
            first = shortages[0]
            raise InsufficientStock(
                'No hay saldo suficiente para registrar la salida.', product_id=first.product_id,
                warehouse_id=warehouse_id, requested=first.requested, available=first.available,
                shortages=shortages)


class ReverseMovement:
    """Revierte un movimiento desde Inventario; con `manual_only` rechaza los que se corrigen desde su documento."""

    def __init__(self, repository: StockMovementRepository, policy: InventoryPolicy | None = None):
        self.repository = repository
        self.policy = policy or BlockNegativeStock()

    def execute(self, movement_id: UUID, *, user_id: UUID | None, user_name: str,
                reason: str, manual_only: bool = False) -> StockMovement:
        original = self.repository.get(movement_id)
        if original is None:
            raise MovementNotFound(movement_id)
        with self.repository.locked(original.warehouse_id):
            original = self.repository.get(movement_id)  # estado vigente, ya bajo el bloqueo
            if manual_only:
                block = reversal_block(original)
                if block is not None:
                    raise MovementConflict(*block)
            counter = original.reverse(
                occurred_at=timezone.now(), user_id=user_id, user_name=user_name, reason=reason)
            if counter.kind is MovementKind.OUT and not self.policy.allow_negative_stock():
                available = self.repository.balance(counter.product_id, counter.warehouse_id)
                if available < counter.quantity:
                    raise InsufficientStock(
                        'No hay saldo suficiente para revertir esta entrada.', product_id=counter.product_id,
                        warehouse_id=counter.warehouse_id, requested=counter.quantity, available=available)
            apply_valuation(self.policy, counter)
            created = self.repository.insert(counter)
            self.repository.mark_reversed(original.id)
            return created


class ReverseSourceMovements:
    """Revierte todos los movimientos confirmados de un documento de origen, todos o ninguno.

    Lo usa el módulo dueño del documento (Compras): un bloqueo por almacén (en orden de id) cubre la validación del
    conjunto y las inserciones. Sin movimientos confirmados pendientes no hace nada.
    """

    def __init__(self, repository: StockMovementRepository, policy: InventoryPolicy | None = None):
        self.repository = repository
        self.policy = policy or BlockNegativeStock()

    def execute(self, source_type: str, source_id: str, *, user_id: UUID | None, user_name: str,
                reason: str) -> list[StockMovement]:
        pending = self._confirmed(source_type, source_id)
        if not pending:
            return []
        with ExitStack() as stack:
            for warehouse_id in sorted({m.warehouse_id for m in pending}, key=str):
                stack.enter_context(self.repository.locked(warehouse_id))
            pending = self._confirmed(source_type, source_id)  # estado vigente, ya bajo el bloqueo
            when = timezone.now()
            counters = [m.reverse(occurred_at=when, user_id=user_id, user_name=user_name, reason=reason)
                        for m in pending]
            self._check_balances(counters)
            for counter in counters:
                apply_valuation(self.policy, counter)
            created = [self.repository.insert(c) for c in counters]
            for original in pending:
                self.repository.mark_reversed(original.id)
            return created

    def _confirmed(self, source_type: str, source_id: str) -> list[StockMovement]:
        return [m for m in self.repository.find_by_source_id(source_type, source_id)
                if m.status is MovementStatus.CONFIRMED]

    def _check_balances(self, counters: list[StockMovement]) -> None:
        if self.policy.allow_negative_stock():
            return
        outputs: dict[tuple[UUID, UUID], Decimal] = {}
        for counter in counters:
            if counter.kind is MovementKind.OUT:
                key = (counter.warehouse_id, counter.product_id)
                outputs[key] = outputs.get(key, Decimal('0')) + counter.quantity
        shortages: list[tuple[UUID, Shortage]] = []
        for (warehouse_id, product_id), requested in outputs.items():
            available = self.repository.balance(product_id, warehouse_id)
            if available < requested:
                shortages.append((warehouse_id, Shortage(product_id, requested, available)))
        if shortages:
            warehouse_id, first = shortages[0]
            raise InsufficientStock(
                'No hay saldo suficiente para revertir esta entrada.', product_id=first.product_id,
                warehouse_id=warehouse_id, requested=first.requested, available=first.available,
                shortages=[s for _, s in shortages])


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
