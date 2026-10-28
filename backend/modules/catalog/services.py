"""Fachada pública del módulo Catalog para otros módulos (p. ej. Sales).

Es la única vía de entrada entre módulos: devuelve DTO inmutables, nunca entidades ni modelos.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from modules.catalog.infrastructure.django.models import ProductModel
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


@dataclass(frozen=True)
class StockProduct:
    """Lo que Inventario necesita saber de un producto para manejar existencias."""

    id: UUID
    name: str
    active: bool
    tracks_stock: bool
    base_unit_name: str | None
    base_unit_abbreviation: str | None
    allows_fractions: bool


def get_stock_products(company_id: UUID, product_ids: Iterable[UUID]) -> dict[UUID, StockProduct]:
    """Los productos de la empresa indicados, por id (los inexistentes o de otra empresa no aparecen). Una consulta."""
    ids = list(set(product_ids))
    if not ids:
        return {}
    models = ProductModel.objects.filter(company_id=company_id, pk__in=ids).select_related('base_unit')
    result: dict[UUID, StockProduct] = {}
    for model in models:
        unit = model.base_unit
        result[model.id] = StockProduct(
            id=model.id, name=model.name, active=model.active, tracks_stock=model.tracks_stock,
            base_unit_name=unit.name if unit else None,
            base_unit_abbreviation=unit.abbreviation if unit else None,
            allows_fractions=bool(unit and unit.allows_fractions))
    return result
