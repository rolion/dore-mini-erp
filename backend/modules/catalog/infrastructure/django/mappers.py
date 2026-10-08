from modules.catalog.domain.product import Product

from .models import ProductModel


def to_entity(model: ProductModel) -> Product:
    return Product(
        id=model.id,
        name=model.name,
        description=model.description,
        sale_price=model.sale_price,
        active=model.active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def to_model_values(product: Product) -> dict[str, object]:
    return {
        'name': product.name,
        'description': product.description,
        'sale_price': product.sale_price,
        'active': product.active,
    }
