from decimal import Decimal
from typing import Sequence
from uuid import UUID

from modules.inventory.domain.adjustment import (
    SOURCE_TYPE,
    StockAdjustment,
    validate_counted_quantity,
    validate_expected_balance,
    validate_reason,
)
from modules.inventory.domain.exceptions import (
    AdjustmentIdReused,
    AdjustmentNotFound,
    AdjustmentValidationError,
    BalanceChanged,
    MovementValidationError,
    WarehouseNotFound,
)
from modules.inventory.domain.movement import MovementSource
from modules.inventory.domain.repositories import (
    AdjustmentFilters,
    StockAdjustmentRepository,
    StockMovementRepository,
    WarehouseRepository,
)
from modules.inventory.domain.stock import check_quantity_for_unit

from .movement_ports import InventoryPolicy, ProductDirectory
from .movement_use_cases import RecordMovement


class ConfirmAdjustment:
    """Confirma un ajuste: calcula la diferencia con el saldo vigente y registra el movimiento de ajuste.

    Todo bajo el bloqueo del almacén y en una transacción. Reintentar la misma clave devuelve el ajuste ya
    registrado (antes de comparar saldos); si el saldo cambió desde el conteo, no registra nada.
    """

    def __init__(self, stock: StockMovementRepository, adjustments: StockAdjustmentRepository,
                 warehouses: WarehouseRepository, products: ProductDirectory, policy: InventoryPolicy | None = None):
        self.stock = stock
        self.adjustments = adjustments
        self.warehouses = warehouses
        self.products = products
        self.recorder = RecordMovement(stock, warehouses, products, policy)

    def execute(self, *, adjustment_id: UUID, product_id: UUID, warehouse_id: UUID, counted_quantity: object,
                expected_system_quantity: object, reason: object, user_id: UUID | None,
                user_name: str) -> tuple[StockAdjustment, bool]:
        counted, expected, reason_text = self._validate(
            product_id, counted_quantity, expected_system_quantity, reason)
        with self.stock.locked(warehouse_id):
            warehouse = self.warehouses.get(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(warehouse_id)
            existing = self.adjustments.get(adjustment_id)
            if existing is not None:  # reintento de una confirmación ya registrada
                same = (existing.product_id, existing.warehouse_id, existing.counted_quantity, existing.reason) == (
                    product_id, warehouse_id, counted, reason_text)
                if not same:
                    raise AdjustmentIdReused()
                return existing, False
            if not warehouse.active:
                raise AdjustmentValidationError({'warehouse_id': ['El almacén debe estar activo.']})
            current = self.stock.balance(product_id, warehouse_id)
            if current != expected:
                raise BalanceChanged(current)
            adjustment = StockAdjustment.create(
                adjustment_id=adjustment_id, product_id=product_id, warehouse_id=warehouse_id,
                system_quantity=current, counted_quantity=counted, reason=reason_text, user_id=user_id,
                user_name=user_name)
            try:
                movement, _ = self.recorder.execute(
                    product_id=product_id, warehouse_id=warehouse_id, kind=adjustment.kind,
                    quantity=abs(adjustment.difference), user_id=user_id, user_name=user_name,
                    reference=adjustment.reference, reason=reason_text,
                    source=MovementSource(SOURCE_TYPE, str(adjustment_id)))
            except MovementValidationError as exc:
                raise AdjustmentValidationError(exc.errors) from exc
            return self.adjustments.insert(adjustment.with_movement(movement.id)), True

    def _validate(self, product_id: UUID, counted_quantity: object, expected: object,
                  reason: object) -> tuple[Decimal, Decimal, str]:
        errors: dict[str, list[str]] = {}
        values: dict[str, object] = {}
        for name, check, raw in (('counted', validate_counted_quantity, counted_quantity),
                                 ('expected', validate_expected_balance, expected),
                                 ('reason', validate_reason, reason)):
            try:
                values[name] = check(raw)
            except AdjustmentValidationError as exc:
                errors.update(exc.errors)
        product = self.products.get_products([product_id]).get(product_id)
        if product is None:
            errors['product_id'] = ['El producto no existe.']
        elif not product.tracks_stock:
            errors['product_id'] = ['El producto no controla stock.']
        elif 'counted' in values:
            message = check_quantity_for_unit(values['counted'], product.allows_fractions)
            if message:
                errors['counted_quantity'] = [message]
        if errors:
            raise AdjustmentValidationError(errors)
        return values['counted'], values['expected'], values['reason']


class GetAdjustmentBalance:
    """Saldo vigente del producto en el almacén, para el formulario."""

    def __init__(self, stock: StockMovementRepository):
        self.stock = stock

    def execute(self, product_id: UUID, warehouse_id: UUID) -> Decimal:
        return self.stock.balance(product_id, warehouse_id)


class ListAdjustments:
    def __init__(self, adjustments: StockAdjustmentRepository):
        self.adjustments = adjustments

    def execute(self, filters: AdjustmentFilters) -> Sequence[StockAdjustment]:
        return self.adjustments.list(filters)


class GetAdjustment:
    def __init__(self, adjustments: StockAdjustmentRepository):
        self.adjustments = adjustments

    def execute(self, adjustment_id: UUID) -> StockAdjustment:
        adjustment = self.adjustments.get(adjustment_id)
        if adjustment is None:
            raise AdjustmentNotFound(adjustment_id)
        return adjustment
