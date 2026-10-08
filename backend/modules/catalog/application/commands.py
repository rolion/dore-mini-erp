from uuid import UUID

from modules.catalog.domain.exceptions import ProductNotFound, ProductValidationError
from modules.catalog.domain.product import Product
from modules.catalog.domain.repositories import ProductRepository

UNSET = object()


class CreateProduct:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def execute(self, name: object, sale_price: object, description: str = '') -> Product:
        product = Product.create(name=name, sale_price=sale_price, description=description)
        return self.repository.save(product)


class UpdateProduct:
    """Edición parcial de datos comerciales; el estado (`active`) no se cambia por aquí."""

    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def execute(self, product_id: UUID, name: object = UNSET, description: object = UNSET,
                sale_price: object = UNSET) -> Product:
        product = self.repository.get(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        errors: dict[str, list[str]] = {}
        changes = (
            (name, product.rename),
            (description, product.describe),
            (sale_price, product.change_price),
        )
        changed = False
        for value, apply in changes:
            if value is UNSET:
                continue
            try:
                apply(value)
                changed = True
            except ProductValidationError as exc:
                errors.update(exc.errors)
        if errors:
            raise ProductValidationError(errors)
        return self.repository.save(product) if changed else product


class ActivateProduct:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def execute(self, product_id: UUID) -> Product:
        product = self.repository.get(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        product.activate()
        return self.repository.save(product)


class DeactivateProduct:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def execute(self, product_id: UUID) -> Product:
        product = self.repository.get(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        product.deactivate()
        return self.repository.save(product)
