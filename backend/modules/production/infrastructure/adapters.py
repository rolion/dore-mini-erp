"""Puente de Producción hacia la fachada pública de Catálogo."""
from collections.abc import Iterable
from uuid import UUID

from modules.catalog import services as catalog_services
from modules.production.application.recipes import ProductInfo


class CatalogProducts:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def products(self, product_ids: Iterable[UUID]) -> dict[UUID, ProductInfo]:
        found = catalog_services.get_products_for_production(self.company_id, product_ids)
        return {pid: ProductInfo(p.id, p.name, p.active, p.unit_id, p.unit_abbreviation, p.allows_fractions)
                for pid, p in found.items()}
