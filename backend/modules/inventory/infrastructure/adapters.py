"""Adaptadores de los puertos de Inventario sobre las fachadas públicas de otros módulos.

Es el único lugar de Inventario que conoce a Catalog, y solo por su `services.py`.
"""
from collections.abc import Iterable
from uuid import UUID

from modules.catalog import services as catalog_services
from modules.inventory.application.movement_ports import ProductInfo


def _info(p) -> ProductInfo:
    return ProductInfo(
        id=p.id, name=p.name, tracks_stock=p.tracks_stock, unit_abbreviation=p.unit_abbreviation,
        allows_fractions=p.allows_fractions, active=p.active)


class CatalogProductDirectory:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get_products(self, product_ids: Iterable[UUID]) -> dict[UUID, ProductInfo]:
        found = catalog_services.get_products_for_inventory(self.company_id, product_ids)
        return {product_id: _info(p) for product_id, p in found.items()}

    def list_stock_products(self, search: str | None = None, active: bool | None = None) -> list[ProductInfo]:
        return [_info(p) for p in catalog_services.list_products_for_inventory(
            self.company_id, search=search, active=active)]
