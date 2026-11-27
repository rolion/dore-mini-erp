"""Puente de Producción hacia la fachada pública de Catálogo."""
from collections.abc import Iterable
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from modules.catalog import services as catalog_services
from modules.costing import services as costing_services
from modules.inventory import services as inventory_services
from modules.modularity import services as modularity_services
from modules.production.application.orders import Actor, LotView, WarehouseView
from modules.production.application.recipes import ProductInfo
from modules.production.domain.packing import Packing
from modules.production.domain.production_order import (
    IngredientShortage, InsufficientIngredients, OrderValidationError, ProductionOrder, RefrigerationRejected)
from shared import module_gate

SOURCE_TYPE = 'production_order'
PACKING_SOURCE_TYPE = 'production_packing'
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
        self._check_lines(order, lines)
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

    def _check_lines(self, order: ProductionOrder, lines: list[tuple[UUID, Decimal]]) -> None:
        """Errores por línea (en el orden de la orden): ingredientes sin control de stock o sin fracciones."""
        quantities = dict(lines)
        tracked = inventory_services.get_stock_products(self.company_id, list(quantities))
        errors: list[dict] = []
        for line in order.ingredients:
            quantity = quantities.get(line.product_id)
            product = tracked.get(line.product_id)
            if quantity is None:
                errors.append({})
            elif product is None:
                errors.append({'actual_quantity': ['El ingrediente no controla stock.']})
            elif not product.allows_fractions and quantity != quantity.to_integral_value():
                errors.append({'actual_quantity': ['Este ingrediente solo admite cantidades enteras.']})
            else:
                errors.append({})
        if any(errors):
            raise OrderValidationError({'ingredients': errors})

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

    def release_lot(self, order: ProductionOrder, actor: Actor) -> None:
        try:
            inventory_services.release_lot(self.company_id, order.lot_id, user_id=actor.user_id,
                                           user_name=actor.user_name)
        except inventory_services.LotNotFound as exc:
            raise RefrigerationRejected('lot_not_found', 'El lote de la orden ya no existe en Inventario.') from exc

    def lot_available(self, order: ProductionOrder) -> Decimal:
        """Saldo a granel: disponible del lote de la orden (0 si no existe)."""
        if order.lot_id is None:
            return Decimal('0')
        try:
            return inventory_services.get_lot(self.company_id, order.lot_id).available_quantity
        except inventory_services.LotNotFound:
            return Decimal('0')

    def pack_out(self, order: ProductionOrder, packing: Packing, when: datetime, actor: Actor) -> None:
        wanted = [packing.pack_product_id, packing.bag_product_id]
        if packing.label_product_id:
            wanted.append(packing.label_product_id)
        tracked = inventory_services.get_stock_products(self.company_id, wanted)
        errors = {}
        if packing.pack_product_id not in tracked:
            errors['pack_product_id'] = ['El producto pack no controla stock.']
        if packing.bag_product_id not in tracked:
            errors['bag_product_id'] = ['El producto bolsa no controla stock.']
        if packing.label_product_id and packing.label_product_id not in tracked:
            errors['label_product_id'] = ['El producto etiqueta no controla stock.']
        if errors:
            raise OrderValidationError(errors)
        supplies = [(packing.bag_product_id, packing.bag_product_name, packing.bags_quantity, 'bag')]
        if packing.label_product_id:
            supplies.append((packing.label_product_id, packing.label_product_name, packing.labels_quantity, 'label'))
        balances = inventory_services.get_balances(
            self.company_id, order.warehouse_id, [s[0] for s in supplies], unlotted=True)
        shortages = []
        bulk_available = self.lot_available(order)
        if bulk_available < packing.bulk_quantity:
            shortages.append(IngredientShortage(order.result_product_id, order.result_product_name,
                                                order.result_unit_abbreviation, packing.bulk_quantity,
                                                bulk_available))
        for product_id, name, required, _line in supplies:
            available = balances.get(product_id, Decimal('0'))
            if available < required:
                shortages.append(IngredientShortage(product_id, name, tracked[product_id].unit_abbreviation,
                                                    required, available))
        if shortages:
            raise InsufficientIngredients(shortages)
        reference = order_reference(order)
        try:
            for product_id, quantity, line, lot_id in (
                    [(order.result_product_id, packing.bulk_quantity, 'bulk', order.lot_id)]
                    + [(pid, qty, ln, None) for pid, _name, qty, ln in supplies]):
                self._record(order.warehouse_id, product_id, 'out', quantity, packing, line, lot_id, reference,
                             when, actor)
        except inventory_services.InsufficientStock as exc:  # carrera con otro documento: se revierte todo
            names = {order.result_product_id: order.result_product_name, **{s[0]: s[1] for s in supplies}}
            raise InsufficientIngredients([
                IngredientShortage(s.product_id, names.get(s.product_id, ''), None, s.requested, s.available)
                for s in exc.shortages]) from exc

    def pack_in(self, packing: Packing, when: datetime, actor: Actor) -> None:
        warehouse_id = inventory_services.get_lot(self.company_id, packing.lot_id).warehouse_id
        self._record(warehouse_id, packing.pack_product_id, 'in', Decimal(packing.packs), packing, 'pack', None,
                     f'EMP-{packing.id.hex[:8].upper()}', when, actor)

    def _record(self, warehouse_id: UUID, product_id: UUID, kind: str, quantity: Decimal, packing: Packing,
                line: str, lot_id: UUID | None, reference: str, when: datetime, actor: Actor) -> None:
        try:
            inventory_services.record_movement(
                self.company_id, product_id=product_id, warehouse_id=warehouse_id, kind=kind, quantity=quantity,
                user_id=actor.user_id, user_name=actor.user_name, reference=reference,
                source_type=PACKING_SOURCE_TYPE, source_id=str(packing.id), source_line=line, occurred_at=when,
                lot_id=lot_id)
        except inventory_services.MovementValidationError as exc:
            raise OrderValidationError({'non_field_errors': [m for msgs in exc.errors.values() for m in msgs]}
                                       ) from exc
        except inventory_services.InsufficientStock:
            raise
        except inventory_services.MovementConflict as exc:
            raise RefrigerationRejected(exc.code, str(exc)) from exc


class ModularityReleasePolicy:
    """Mínimo de refrigeración desde la fachada de lectura de Modularidad."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def min_refrigeration_hours(self) -> int:
        return modularity_services.get_production_settings(self.company_id).min_refrigeration_hours


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

    def cost_packing_outputs(self, order: ProductionOrder, packing: Packing, when: datetime) -> Decimal | None:
        """Valoriza cuñapés y bolsas al promedio de Costeo; `None` sin Costeo o sin costo (INV-07)."""
        if not self._active():
            return None
        lines = [(order.result_product_id, packing.bulk_quantity), (packing.bag_product_id, packing.bags_quantity)]
        if packing.label_product_id:
            lines.append((packing.label_product_id, packing.labels_quantity))
        try:
            costed = costing_services.cost_outputs(
                self.company_id, source_type=PACKING_SOURCE_TYPE, source_id=str(packing.id),
                lines=lines, occurred_at=when)
        except costing_services.CostUnavailable:
            return None
        return costed.total

    def cost_packing_entry(self, packing: Packing, total_cost: Decimal, when: datetime) -> Decimal:
        unit_cost = (total_cost / packing.packs).quantize(_UNIT_COST_STEP, rounding=ROUND_HALF_UP)
        costing_services.cost_receipt(
            self.company_id, source_type=PACKING_SOURCE_TYPE, source_id=str(packing.id),
            lines=[(packing.pack_product_id, Decimal(packing.packs), unit_cost)], occurred_at=when)
        return unit_cost
