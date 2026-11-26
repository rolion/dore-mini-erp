"""Casos de uso de recetas; validan contra Catálogo por el puerto `ProductCatalog`."""
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from modules.production.domain.recipe import Recipe, RecipeIngredient, RecipeNotFound, RecipeValidationError


@dataclass(frozen=True)
class ProductInfo:
    id: UUID
    name: str
    active: bool
    unit_id: UUID | None
    unit_abbreviation: str | None
    allows_fractions: bool


class ProductCatalog(Protocol):
    def products(self, product_ids: Iterable[UUID]) -> dict[UUID, ProductInfo]: ...


class RecipeRepository(Protocol):
    def get(self, recipe_id: UUID, *, for_update: bool = False) -> Recipe | None: ...
    def save(self, recipe: Recipe) -> Recipe: ...
    def list(self, *, search: str = '', status: str = 'active'): ...
    def name_taken(self, name: str, *, exclude_id: UUID) -> bool: ...


def _check_quantity(quantity: Decimal, product: ProductInfo, label: str) -> str | None:
    if quantity != quantity.to_integral_value() and not product.allows_fractions:
        return f'{label} no admite fracciones: la unidad de {product.name} es entera.'
    return None


class RecipeBook:
    def __init__(self, repository: RecipeRepository, catalog: ProductCatalog):
        self.repository = repository
        self.catalog = catalog

    def get(self, recipe_id: UUID, *, for_update: bool = False) -> Recipe:
        recipe = self.repository.get(recipe_id, for_update=for_update)
        if recipe is None:
            raise RecipeNotFound
        return recipe

    def _validate_against_catalog(self, recipe: Recipe) -> None:
        ids = {recipe.result_product_id, *(line.product_id for line in recipe.ingredients)}
        products = self.catalog.products(ids)
        errors: dict = {}
        result = products.get(recipe.result_product_id)
        if result is None:
            errors['result_product_id'] = ['El producto resultante no existe.']
        elif not result.active:
            errors['result_product_id'] = ['El producto resultante está inactivo.']
        elif result.unit_id is None:
            errors['result_product_id'] = ['El producto resultante no tiene unidad base.']
        else:
            message = _check_quantity(recipe.yield_quantity, result, 'El rendimiento base')
            if message:
                errors['yield_quantity'] = [message]
        line_errors: list[dict] = []
        for line in recipe.ingredients:
            problem: dict = {}
            product = products.get(line.product_id)
            if product is None:
                problem['product_id'] = ['El producto no existe.']
            elif not product.active:
                problem['product_id'] = ['El producto está inactivo.']
            elif product.unit_id is None:
                problem['product_id'] = ['El producto no tiene unidad base.']
            else:
                if line.unit_id != product.unit_id:
                    problem['unit_id'] = ['La unidad debe ser la unidad base del producto.']
                message = _check_quantity(line.quantity, product, 'La cantidad')
                if message:
                    problem['quantity'] = [message]
            line_errors.append(problem)
        if any(line_errors):
            errors['ingredients'] = line_errors
        if errors:
            raise RecipeValidationError(errors)

    def _validate(self, recipe: Recipe) -> None:
        try:
            self._validate_against_catalog(recipe)
        except RecipeValidationError as exc:
            errors = dict(exc.errors)
        else:
            errors = {}
        if self.repository.name_taken(recipe.name, exclude_id=recipe.id):
            errors['name'] = ['Ya existe una receta con este nombre en tu empresa.']
        if errors:
            raise RecipeValidationError(errors)

    def create(self, *, name, result_product_id, yield_quantity, ingredients: list[RecipeIngredient]) -> Recipe:
        recipe = Recipe.create(name=name, result_product_id=result_product_id,
                               yield_quantity=yield_quantity, ingredients=ingredients)
        self._validate(recipe)
        return self.repository.save(recipe)

    def update(self, recipe_id: UUID, *, name, result_product_id, yield_quantity,
               ingredients: list[RecipeIngredient]) -> Recipe:
        previous = self.get(recipe_id, for_update=True)
        recipe = previous.redefined(name=name, result_product_id=result_product_id,
                                    yield_quantity=yield_quantity, ingredients=ingredients)
        self._validate(recipe)
        return self.repository.save(recipe)

    def set_active(self, recipe_id: UUID, *, active: bool) -> Recipe:
        recipe = self.get(recipe_id, for_update=True)
        if active:
            recipe.activate()
        else:
            recipe.deactivate()
        return self.repository.save(recipe)
