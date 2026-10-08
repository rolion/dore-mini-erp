"""Puertos que Sales necesita del exterior: otros módulos y el reloj.

Las implementaciones viven en `infrastructure/` (adaptadores sobre las fachadas `services.py` de Catalog y Customers).
"""
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ProductInfo:
    id: UUID
    name: str
    sale_price: Decimal
    active: bool


@dataclass(frozen=True)
class CustomerInfo:
    id: UUID
    name: str
    active: bool


class ProductCatalog(Protocol):
    def get_product_for_sale(self, product_id: UUID) -> ProductInfo | None: ...


class CustomerDirectory(Protocol):
    def get_customer_for_sale(self, customer_id: UUID) -> CustomerInfo | None: ...

    def get_customer_names(self, customer_ids: Iterable[UUID]) -> dict[UUID, str]: ...


class Clock(Protocol):
    def today(self) -> date: ...

    def now(self) -> datetime: ...
