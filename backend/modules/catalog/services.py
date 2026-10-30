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
    sale_price: Decimal | None
    active: bool
    can_sell: bool = True


def get_product_for_sale(company_id: UUID, product_id: UUID) -> ProductForSale | None:
    """El producto de la empresa con su nombre y precio vigentes, o `None` si no existe (o es de otra empresa).

    Las reglas de "activo" y "se puede vender" las aplica quien vende, no la fachada.
    """
    product = DjangoProductRepository(company_id).get(product_id)
    if product is None:
        return None
    return ProductForSale(id=product.id, name=product.name, sale_price=product.sale_price, active=product.active,
                          can_sell=product.can_sell)


@dataclass(frozen=True)
class ProductForPurchase:
    id: UUID
    name: str
    active: bool
    can_buy: bool
    # Unidad base (opcional): el producto puede no tenerla; sin unidad se tratan cantidades con fracciones.
    unit_abbreviation: str | None = None
    allows_fractions: bool = False


def _for_purchase(model: ProductModel) -> ProductForPurchase:
    unit = model.base_unit
    return ProductForPurchase(
        id=model.id, name=model.name, active=model.active, can_buy=model.can_buy,
        unit_abbreviation=unit.abbreviation if unit else None,
        allows_fractions=bool(unit and unit.allows_fractions))


def get_product_for_purchase(company_id: UUID, product_id: UUID) -> ProductForPurchase | None:
    """El producto de la empresa con sus usos, o `None` si no existe (o es de otra empresa).

    Una compra solo debe aceptar productos activos y comprables; esa regla la aplica quien compra.
    """
    model = ProductModel.objects.filter(company_id=company_id, pk=product_id).select_related('base_unit').first()
    return _for_purchase(model) if model else None


@dataclass(frozen=True)
class ProductForInventory:
    id: UUID
    name: str
    tracks_stock: bool
    unit_abbreviation: str | None
    allows_fractions: bool
    active: bool = True


def _for_inventory(model: ProductModel) -> ProductForInventory:
    return ProductForInventory(
        id=model.id, name=model.name, tracks_stock=model.tracks_stock,
        unit_abbreviation=model.base_unit.abbreviation if model.base_unit else None,
        allows_fractions=bool(model.base_unit and model.base_unit.allows_fractions), active=model.active)


def get_products_for_inventory(company_id: UUID, product_ids: Iterable[UUID]) -> dict[UUID, ProductForInventory]:
    """Datos de inventario de los productos de la empresa (una sola consulta); los ajenos o inexistentes no aparecen."""
    models = (ProductModel.objects.filter(company_id=company_id, pk__in=list(product_ids))
              .select_related('base_unit'))
    return {model.id: _for_inventory(model) for model in models}


def list_products_for_inventory(company_id: UUID, *, search: str | None = None,
                                active: bool | None = None) -> list[ProductForInventory]:
    """Productos de la empresa que controlan stock, por nombre; `active=None` incluye activos e inactivos."""
    queryset = (ProductModel.objects.filter(company_id=company_id, tracks_stock=True)
                .select_related('base_unit').order_by('name', 'id'))
    if search:
        queryset = queryset.filter(name__icontains=search)
    if active is not None:
        queryset = queryset.filter(active=active)
    return [_for_inventory(model) for model in queryset]


def get_products_for_purchase(company_id: UUID, product_ids: Iterable[UUID]) -> dict[UUID, ProductForPurchase]:
    """Datos de compra de los productos de la empresa (una sola consulta); los ajenos o inexistentes no aparecen.

    Las reglas de "producto activo" y "comprable" las aplica quien compra, no la fachada.
    """
    models = (ProductModel.objects.filter(company_id=company_id, pk__in=list(product_ids))
              .select_related('base_unit'))
    return {model.id: _for_purchase(model) for model in models}
