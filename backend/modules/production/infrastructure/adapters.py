"""Puente de Producción hacia la fachada pública de Catálogo."""
from collections.abc import Iterable
from uuid import UUID

from modules.catalog import services as catalog_services
from modules.inventory import services as inventory_services
from modules.production.application.orders import WarehouseView
from modules.production.application.recipes import ProductInfo


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
