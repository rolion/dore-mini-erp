"""Puertos que Purchases necesita de otros módulos. Su implementación vive en `infrastructure/adapters.py`."""
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ProductInfo:
    id: UUID
    name: str
    active: bool
    can_buy: bool
    unit_abbreviation: str | None
    allows_fractions: bool


class ProductCatalog(Protocol):
    def get_products(self, product_ids: Iterable[UUID]) -> dict[UUID, ProductInfo]: ...
