"""Fachada pública del módulo Catalog para otros módulos (p. ej. Sales).

Es la única vía de entrada entre módulos: devuelve DTO inmutables, nunca entidades ni modelos.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from modules.catalog.infrastructure.django.repositories import DjangoProductRepository


@dataclass(frozen=True)
class ProductForSale:
    id: UUID
    name: str
    sale_price: Decimal
    active: bool


def get_product_for_sale(company_id: UUID, product_id: UUID) -> ProductForSale | None:
    """El producto de la empresa con su nombre y precio vigentes, o `None` si no existe (o es de otra empresa).

    La regla de "producto activo" la aplica quien vende, no la fachada.
    """
    product = DjangoProductRepository(company_id).get(product_id)
    if product is None:
        return None
    return ProductForSale(id=product.id, name=product.name, sale_price=product.sale_price, active=product.active)
