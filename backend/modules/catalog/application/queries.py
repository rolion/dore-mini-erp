from typing import Sequence
from uuid import UUID

from modules.catalog.domain.exceptions import ProductNotFound, UnitNotFound
from modules.catalog.domain.product import Product
from modules.catalog.domain.repositories import ProductRepository, UnitRepository
from modules.catalog.domain.unit import UnitOfMeasure


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

    def execute(self, search: str | None = None, active: bool | None = None,
                tracks_stock: bool | None = None) -> Sequence[Product]:
        return self.repository.list(search=search, active=active, tracks_stock=tracks_stock)


class GetUnit:
    def __init__(self, repository: UnitRepository):
        self.repository = repository

    def execute(self, unit_id: UUID) -> UnitOfMeasure:
        unit = self.repository.get(unit_id)
        if unit is None:
            raise UnitNotFound(unit_id)
        return unit


class ListUnits:
    def __init__(self, repository: UnitRepository):
        self.repository = repository

    def execute(self, search: str | None = None, active: bool | None = None) -> Sequence[UnitOfMeasure]:
        return self.repository.list(search=search, active=active)
