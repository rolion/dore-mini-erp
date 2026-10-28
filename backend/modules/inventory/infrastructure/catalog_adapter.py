from uuid import UUID

from modules.catalog import services as catalog_services
from modules.inventory.application.ports import ProductInfo


class CatalogProducts:
    """Lee productos solo por la fachada pública de Catálogo (ningún modelo ajeno)."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get_products(self, product_ids: list[UUID]) -> dict[UUID, ProductInfo]:
        found = catalog_services.get_stock_products(self.company_id, product_ids)
        return {
            product_id: ProductInfo(
                id=item.id, name=item.name, active=item.active, tracks_stock=item.tracks_stock,
                unit_name=item.base_unit_name, unit_abbreviation=item.base_unit_abbreviation,
                allows_fractions=item.allows_fractions)
            for product_id, item in found.items()}
