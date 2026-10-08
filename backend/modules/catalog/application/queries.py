from typing import Sequence
from uuid import UUID

from modules.catalog.domain.exceptions import ProductNotFound
from modules.catalog.domain.product import Product
from modules.catalog.domain.repositories import ProductRepository


class GetProduct:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def execute(self, product_id: UUID) -> Product:
        product = self.repository.get(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        return product


class ListProducts:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def execute(self, search: str | None = None, active: bool | None = None) -> Sequence[Product]:
        return self.repository.list(search=search, active=active)
