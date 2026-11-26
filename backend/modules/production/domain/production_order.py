"""Agregado Orden de producción (sin Django): copia de la receta, preparaciones previstas y estado."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

PREPARATIONS_MAX = 99999
_STEP = Decimal('0.0001')


class OrderStatus:
    DRAFT = 'draft'
    IN_PREPARATION = 'in_preparation'
    ALL = (DRAFT, IN_PREPARATION)


class OrderValidationError(Exception):
    """`errors`: {campo: [mensajes]}."""

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(errors)


class OrderNotFound(Exception):
    pass


class OrderStateError(Exception):
    """La orden no está en el estado que exige la operación."""


def parse_preparations(raw: object) -> int:
    """Entero positivo; rechaza `bool`, decimales, texto no numérico y valores fuera de rango."""
    if isinstance(raw, bool):
        raise ValueError('El número de preparaciones debe ser un entero positivo.')
    if isinstance(raw, str):
        text = raw.strip()
        if not (text.isascii() and text.isdigit()) or len(text) > 9:
            raise ValueError('El número de preparaciones debe ser un entero positivo.')
        value = int(text)
    elif isinstance(raw, int):
        value = raw
    else:
        raise ValueError('El número de preparaciones debe ser un entero positivo.')
    if value < 1:
        raise ValueError('El número de preparaciones debe ser un entero positivo.')
    if value > PREPARATIONS_MAX:
        raise ValueError(f'El número de preparaciones no puede superar {PREPARATIONS_MAX}.')
    return value


@dataclass(frozen=True)
class OrderIngredient:
    product_id: UUID
    product_name: str
    unit_id: UUID | None
    unit_abbreviation: str | None
    quantity_per_preparation: Decimal


@dataclass
class ProductionOrder:
    id: UUID
    recipe_id: UUID
    recipe_name: str
    result_product_id: UUID
    result_product_name: str
    result_unit_id: UUID | None
    result_unit_abbreviation: str | None
    yield_per_preparation: Decimal
    warehouse_id: UUID
    preparations: int
    ingredients: list[OrderIngredient] = field(default_factory=list)
    status: str = OrderStatus.DRAFT
    number: int | None = None
    started_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, *, recipe_id, recipe_name, result_product_id, result_product_name, result_unit_id,
               result_unit_abbreviation, yield_per_preparation: Decimal, warehouse_id: UUID, preparations: object,
               ingredients: list[OrderIngredient]) -> 'ProductionOrder':
        try:
            count = parse_preparations(preparations)
        except ValueError as exc:
            raise OrderValidationError({'preparations': [str(exc)]}) from None
        return cls(uuid4(), recipe_id, recipe_name, result_product_id, result_product_name, result_unit_id,
                   result_unit_abbreviation, yield_per_preparation, warehouse_id, count, list(ingredients))

    @property
    def expected_output(self) -> Decimal:
        return (self.yield_per_preparation * self.preparations).quantize(_STEP)

    def expected_quantity(self, line: OrderIngredient) -> Decimal:
        return (line.quantity_per_preparation * self.preparations).quantize(_STEP)

    def change_plan(self, *, warehouse_id: UUID, preparations: object) -> None:
        """Solo en borrador: cambia almacén y preparaciones; la copia de la receta no se toca."""
        if self.status != OrderStatus.DRAFT:
            raise OrderStateError('Solo se puede editar una orden en borrador.')
        try:
            count = parse_preparations(preparations)
        except ValueError as exc:
            raise OrderValidationError({'preparations': [str(exc)]}) from None
        self.warehouse_id = warehouse_id
        self.preparations = count

    def start(self, now: datetime) -> None:
        if self.status != OrderStatus.DRAFT:
            raise OrderStateError('La orden ya fue iniciada.')
        self.status = OrderStatus.IN_PREPARATION
        self.started_at = now
