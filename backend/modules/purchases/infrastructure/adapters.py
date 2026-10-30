"""Adaptadores de los puertos de Purchases sobre las fachadas públicas de otros módulos.

Es el único lugar de Purchases que conoce a Catalog e Inventory, y solo por su `services.py`.
"""
from collections.abc import Iterable
from uuid import UUID

from decimal import Decimal

from modules.catalog import services as catalog_services
from modules.inventory import services as inventory_services
from modules.purchases.application.ports import (
    Actor,
    ProductInfo,
    StockEntryMovement,
    StockProductInfo,
    StockWarehouse,
)
from modules.purchases.domain.exceptions import PurchaseValidationError, StockShortage
from shared import module_gate

INVENTORY_MODULE = 'inventory'


class ProductCatalogAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get_products(self, product_ids: Iterable[UUID]) -> dict[UUID, ProductInfo]:
        products = catalog_services.get_products_for_purchase(self.company_id, product_ids)
        return {
            pid: ProductInfo(id=p.id, name=p.name, active=p.active, can_buy=p.can_buy, unit_abbreviation=p.unit_abbreviation,
                             allows_fractions=p.allows_fractions)
            for pid, p in products.items()
        }


class StockEntryAdapter:
    """Entradas de inventario al recibir, sobre la fachada de Inventario; es una integración opcional."""

    SOURCE_TYPE = 'purchase_receipt'

    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is None:  # una consulta por adaptador (por petición)
            self._available = module_gate.is_enabled(self.company_id, INVENTORY_MODULE)
        return self._available

    def controlled_products(self, product_ids: Iterable[UUID]) -> dict[UUID, StockProductInfo]:
        found = inventory_services.get_stock_products(self.company_id, product_ids)
        return {pid: StockProductInfo(p.id, p.name, p.unit_abbreviation) for pid, p in found.items()}

    def active_warehouses(self) -> list[StockWarehouse]:
        return [StockWarehouse(w.id, w.name, w.is_default)
                for w in inventory_services.list_active_warehouses(self.company_id)]

    def register_entries(self, warehouse_id: UUID, lines: list[tuple[UUID, Decimal]], receipt_id: UUID,
                         reference: str, actor: Actor, unit_costs: dict[UUID, Decimal] | None = None) -> None:
        for product_id, quantity in lines:
            price = (unit_costs or {}).get(product_id)
            valuation = None if price is None else inventory_services.MovementValue(
                cost_origin='purchase_price', unit_cost=price)
            try:
                inventory_services.record_movement(
                    self.company_id, product_id=product_id, warehouse_id=warehouse_id, kind='in', quantity=quantity,
                    user_id=actor.user_id, user_name=actor.user_name, reference=reference,
                    source_type=self.SOURCE_TYPE, source_id=str(receipt_id), source_line=str(product_id),
                    valuation=valuation)
            except inventory_services.MovementValidationError as exc:
                # Solo el almacén es atribuible a la persona; lo demás se informa sin campo.
                raise PurchaseValidationError({
                    'warehouse_id' if key == 'warehouse_id' else 'non_field_errors': messages
                    for key, messages in exc.errors.items()}) from exc
            except inventory_services.MovementConflict as exc:
                raise PurchaseValidationError({'non_field_errors': [str(exc)]}) from exc

    def reverse_entries(self, receipt_id: UUID, reason: str, actor: Actor) -> None:
        try:
            inventory_services.reverse_source_movements(
                self.company_id, self.SOURCE_TYPE, str(receipt_id), user_id=actor.user_id,
                user_name=actor.user_name, reason=reason)
        except inventory_services.InsufficientStock as exc:
            raise StockShortage(exc.warehouse_id, [(s.product_id, s.requested, s.available)
                                                   for s in exc.shortages]) from exc
        except inventory_services.MovementValidationError as exc:
            raise PurchaseValidationError({'non_field_errors': [m for ms in exc.errors.values() for m in ms]}) from exc
        except inventory_services.MovementConflict as exc:
            raise PurchaseValidationError({'non_field_errors': [str(exc)]}) from exc

    def movements_for(self, receipt_id: UUID) -> list[StockEntryMovement]:
        return [StockEntryMovement(m.id, m.product_id, m.product_name, m.unit_abbreviation, m.warehouse_id,
                                   m.warehouse_name, m.quantity, m.reference, m.status, m.reversed_by_id,
                                   m.reversed_by_reference)
                for m in inventory_services.list_movements_for_source(
                    self.company_id, self.SOURCE_TYPE, str(receipt_id))]
