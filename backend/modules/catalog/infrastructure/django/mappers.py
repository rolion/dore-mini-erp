from modules.catalog.domain.product import Product, UnitSummary
from modules.catalog.domain.unit import UnitOfMeasure

from .models import ProductModel, UnitModel


def to_entity(model: ProductModel) -> Product:
    unit = model.base_unit
    return Product(
        id=model.id,
        name=model.name,
        description=model.description,
        sale_price=model.sale_price,
        active=model.active,
        tracks_stock=model.tracks_stock,
        base_unit_id=model.base_unit_id,
        base_unit=UnitSummary(unit.id, unit.name, unit.abbreviation, unit.allows_fractions) if unit else None,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def to_model_values(product: Product) -> dict[str, object]:
    return {
        'name': product.name,
        'description': product.description,
        'sale_price': product.sale_price,
        'active': product.active,
        'tracks_stock': product.tracks_stock,
        'base_unit_id': product.base_unit_id,
    }


def unit_to_entity(model: UnitModel) -> UnitOfMeasure:
    return UnitOfMeasure(
        id=model.id,
        name=model.name,
        abbreviation=model.abbreviation,
        allows_fractions=model.allows_fractions,
        active=model.active,
        in_use=getattr(model, 'in_use', False),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def unit_to_model_values(unit: UnitOfMeasure) -> dict[str, object]:
    return {
        'name': unit.name,
        'abbreviation': unit.abbreviation,
        'allows_fractions': unit.allows_fractions,
        'active': unit.active,
    }
