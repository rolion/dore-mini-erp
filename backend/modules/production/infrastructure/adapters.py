"""Puente de Producción hacia la fachada pública de Catálogo."""
from collections.abc import Iterable
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from modules.catalog import services as catalog_services
from modules.costing import services as costing_services
from modules.inventory import services as inventory_services
from modules.production.application.orders import Actor, LotView, WarehouseView
from modules.production.application.recipes import ProductInfo
from modules.production.domain.production_order import (
    IngredientShortage, InsufficientIngredients, OrderValidationError, ProductionOrder, RefrigerationRejected)
from shared import module_gate

SOURCE_TYPE = 'production_order'
COSTING_MODULE = 'costing'
_UNIT_COST_STEP = Decimal('0.000001')


class CatalogProducts:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def products(self, product_ids: Iterable[UUID]) -> dict[UUID, ProductInfo]:
        found = catalog_services.get_products_for_production(self.company_id, product_ids)
        return {pid: ProductInfo(p.id, p.name, p.active, p.unit_id, p.unit_abbreviation, p.allows_fractions)
                for pid, p in found.items()}


class InventoryWarehouses:
    """Almacenes de Inventario por su fachada pública (solo lectura)."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def active(self) -> list[WarehouseView]:
        return [WarehouseView(w.id, w.name, w.is_default)
                for w in inventory_services.list_active_warehouses(self.company_id)]

    def names(self, warehouse_ids: Iterable[UUID]) -> dict[UUID, str]:
        return inventory_services.get_warehouse_names(self.company_id, warehouse_ids)


def order_reference(order: ProductionOrder) -> str:
    return f'OP-{order.number:04d}' if order.number else ''


class InventoryStock:
    """Salidas de ingredientes y entrada del granel con lote, por la fachada de Inventario (todo en la transacción
    del llamador)."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def consume(self, order: ProductionOrder, lines: list[tuple[UUID, Decimal]], when: datetime,
                actor: Actor) -> None:
        try:
            inventory_services.record_outputs(
                self.company_id, warehouse_id=order.warehouse_id, lines=lines, source_type=SOURCE_TYPE,
                source_id=str(order.id), user_id=actor.user_id, user_name=actor.user_name,
                reference=order_reference(order), occurred_at=when)
        except inventory_services.InsufficientStock as exc:
            names = inventory_services.get_product_names(self.company_id, [s.product_id for s in exc.shortages])
            raise InsufficientIngredients([
                IngredientShortage(s.product_id, names.get(s.product_id, ('', None))[0],
                                   names.get(s.product_id, ('', None))[1], s.requested, s.available)
                for s in exc.shortages]) from exc
        except inventory_services.MovementValidationError as exc:
            raise OrderValidationError({'non_field_errors': [m for msgs in exc.errors.values() for m in msgs]}) from exc
        except inventory_services.MovementConflict as exc:
            raise RefrigerationRejected(exc.code, str(exc)) from exc

    def enter_lot(self, order: ProductionOrder, quantity: Decimal, when: datetime, actor: Actor) -> LotView:
        try:
            lot, _movement, _created = inventory_services.create_lot(
                self.company_id, product_id=order.result_product_id, warehouse_id=order.warehouse_id,
                quantity=quantity, source_type=SOURCE_TYPE, source_id=str(order.id), user_id=actor.user_id,
                user_name=actor.user_name, reference=order_reference(order), occurred_at=when)
        except inventory_services.MovementValidationError as exc:
            raise OrderValidationError({'actual_output': [m for msgs in exc.errors.values() for m in msgs]}) from exc
        except inventory_services.MovementConflict as exc:  # incluye LotNumberingRejected (período fiscal)
            raise RefrigerationRejected(exc.code, str(exc)) from exc
        return LotView(lot.id, lot.code)


class CostingGateway:
    """Costeo (opcional): valoriza lo consumido y registra la entrada con su costo unitario."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _active(self) -> bool:
        return module_gate.is_enabled(self.company_id, COSTING_MODULE) and costing_services.is_valued(self.company_id)

    def cost_consumption(self, order: ProductionOrder, lines: list[tuple[UUID, Decimal]],
                         when: datetime) -> Decimal | None:
        if not self._active():
            return None
        try:
            costed = costing_services.cost_outputs(
                self.company_id, source_type=SOURCE_TYPE, source_id=str(order.id), lines=lines, occurred_at=when)
        except costing_services.CostUnavailable:
            return None
        return costed.total

    def cost_entry(self, order: ProductionOrder, quantity: Decimal, total_cost: Decimal, when: datetime) -> None:
        unit_cost = (total_cost / quantity).quantize(_UNIT_COST_STEP, rounding=ROUND_HALF_UP)
        costing_services.cost_receipt(
            self.company_id, source_type=SOURCE_TYPE, source_id=str(order.id),
            lines=[(order.result_product_id, quantity, unit_cost)], occurred_at=when)
