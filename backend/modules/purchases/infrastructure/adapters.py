"""Adaptadores de los puertos de Purchases sobre las fachadas públicas de otros módulos.

Es el único lugar de Purchases que conoce a Catalog, y solo por su `services.py`.
"""
from collections.abc import Iterable
from uuid import UUID

from modules.catalog import services as catalog_services
from modules.purchases.application.ports import ProductInfo


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
