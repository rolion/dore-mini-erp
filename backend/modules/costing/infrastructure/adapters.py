"""Adaptador de las existencias de la empresa sobre la fachada pública de Inventario (única puerta entre módulos)."""
from contextlib import AbstractContextManager
from uuid import UUID

from modules.costing.application.use_cases import ProductStock, WarehouseQuantity
from modules.inventory import services as inventory_services


class InventoryCompanyStock:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def locked(self) -> AbstractContextManager[None]:
        return inventory_services.lock_company_stock(self.company_id)

    def snapshot(self) -> list[ProductStock]:
        return [ProductStock(
            product_id=s.product_id, product_name=s.product_name, unit_abbreviation=s.unit_abbreviation,
            quantity=s.quantity,
            warehouses=tuple(WarehouseQuantity(w.warehouse_id, w.warehouse_name, w.quantity) for w in s.warehouses))
            for s in inventory_services.get_company_stock(self.company_id)]

    def names(self, product_ids) -> dict[UUID, tuple[str, str | None]]:
        return inventory_services.get_product_names(self.company_id, list(product_ids))
