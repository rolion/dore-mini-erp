"""Agregado Receta (sin Django): fórmula con producto resultante, rendimiento base e ingredientes."""
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

NAME_MAX_LENGTH = 150
QUANTITY_MAX = Decimal('9999999999.9999')
_STEP = Decimal('0.0001')


class RecipeValidationError(Exception):
    """`errors`: {campo: [mensajes]}; `ingredients` es una lista alineada con las líneas ({} si la línea está bien)."""

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(errors)


class RecipeNotFound(Exception):
    pass


def parse_quantity(raw: object, label: str) -> Decimal:
    """Cantidad positiva con hasta 4 decimales; `float` y `bool` quedan fuera (nunca se maneja como float)."""
    if isinstance(raw, bool) or not isinstance(raw, (Decimal, int, str)):
        raise ValueError(f'{label} debe ser un número decimal.')
    try:
        value = Decimal(raw.strip() if isinstance(raw, str) else raw)
    except InvalidOperation:
        raise ValueError(f'{label} debe ser un número decimal.') from None
    if not value.is_finite():
        raise ValueError(f'{label} debe ser un número decimal.')
    if value <= 0:
        raise ValueError(f'{label} debe ser mayor que cero.')
    if value != value.quantize(_STEP):
        raise ValueError(f'{label} admite como máximo 4 decimales.')
    if value > QUANTITY_MAX:
        raise ValueError(f'{label} no puede superar {QUANTITY_MAX}.')
    return value.quantize(_STEP)


@dataclass
class RecipeIngredient:
    product_id: UUID
    unit_id: UUID | None
    quantity: Decimal


@dataclass
class Recipe:
    id: UUID
    name: str
    result_product_id: UUID
    yield_quantity: Decimal
    ingredients: list[RecipeIngredient] = field(default_factory=list)
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, **values) -> 'Recipe':
        recipe = cls(uuid4(), '', values.get('result_product_id'), Decimal('0'), [])
        return recipe.redefined(**values)

    def redefined(self, *, name: object, result_product_id: UUID, yield_quantity: object,
                  ingredients: list[RecipeIngredient]) -> 'Recipe':
        """Devuelve la receta con nueva definición validada (forma y reglas propias; las de Catálogo, en aplicación)."""
        errors: dict = {}
        clean_name = name.strip() if isinstance(name, str) else ''
        if not clean_name:
            errors['name'] = ['El nombre es obligatorio.']
        elif len(clean_name) > NAME_MAX_LENGTH:
            errors['name'] = [f'El nombre no puede superar {NAME_MAX_LENGTH} caracteres.']
        if not isinstance(result_product_id, UUID):
            errors['result_product_id'] = ['Elige el producto resultante.']
        try:
            clean_yield = parse_quantity(yield_quantity, 'El rendimiento base')
        except ValueError as exc:
            clean_yield = Decimal('0')
            errors['yield_quantity'] = [str(exc)]
        lines: list[RecipeIngredient] = []
        line_errors: list[dict] = []
        seen: set[UUID] = set()
        for ingredient in ingredients:
            problem: dict = {}
            if not isinstance(ingredient.product_id, UUID):
                problem['product_id'] = ['Elige el producto del ingrediente.']
            elif ingredient.product_id in seen:
                problem['product_id'] = ['Este producto ya está en la receta.']
            elif ingredient.product_id == result_product_id:
                problem['product_id'] = ['El producto resultante no puede ser ingrediente de su propia receta.']
            else:
                seen.add(ingredient.product_id)
            quantity = Decimal('0')
            try:
                quantity = parse_quantity(ingredient.quantity, 'La cantidad')
            except ValueError as exc:
                problem['quantity'] = [str(exc)]
            line_errors.append(problem)
            lines.append(RecipeIngredient(ingredient.product_id, ingredient.unit_id, quantity))
        if not lines:
            errors['ingredients'] = ['Agrega al menos un ingrediente.']
        elif any(line_errors):
            errors['ingredients'] = line_errors
        if errors:
            raise RecipeValidationError(errors)
        return replace(self, name=clean_name, result_product_id=result_product_id,
                       yield_quantity=clean_yield, ingredients=lines)

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        self.active = False
