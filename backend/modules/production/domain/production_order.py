"""Agregado Orden de producción (sin Django): copia de la receta, preparaciones previstas y estado."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

PREPARATIONS_MAX = 99999
_STEP = Decimal('0.0001')


class OrderStatus:
    DRAFT = 'draft'
    IN_PREPARATION = 'in_preparation'
    REFRIGERATING = 'refrigerating'
    READY_TO_PACK = 'ready_to_pack'
    ALL = (DRAFT, IN_PREPARATION, REFRIGERATING, READY_TO_PACK)


class OrderValidationError(Exception):
    """`errors`: {campo: [mensajes]}."""

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(errors)


class OrderNotFound(Exception):
    pass


class OrderStateError(Exception):
    """La orden no está en el estado que exige la operación."""


@dataclass(frozen=True)
class IngredientShortage:
    product_id: UUID
    product_name: str
    unit_abbreviation: str | None
    requested: Decimal
    available: Decimal

    @property
    def missing(self) -> Decimal:
        return (self.requested - self.available).quantize(_STEP)


class InsufficientIngredients(Exception):
    """Faltan existencias de uno o más ingredientes; `shortages` los lista todos."""

    def __init__(self, shortages: list[IngredientShortage]):
        self.shortages = shortages
        super().__init__('No hay existencias suficientes de los ingredientes.')


class RefrigerationRejected(Exception):
    """Inventario no puede registrar el lote (p. ej. sin período fiscal abierto); `code` y `message` accionables."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class ReleaseTooEarly(Exception):
    """Aún no se cumple el mínimo de refrigeración; `releasable_from` es la primera hora habilitada."""

    def __init__(self, releasable_from: datetime, min_hours: int):
        self.releasable_from = releasable_from
        self.min_hours = min_hours
        super().__init__('Todavía no se cumple el tiempo mínimo de refrigeración del lote.')


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


QUANTITY_MAX = Decimal('999999999999.9999')
CLOCK_TOLERANCE = timedelta(minutes=5)


def parse_quantity(raw: object, *, allow_zero: bool) -> Decimal:
    """Decimal finito de a lo sumo 4 decimales; rechaza `bool`, texto, negativos y (si no se admite) cero."""
    if isinstance(raw, bool) or not isinstance(raw, (int, str, Decimal)):
        raise ValueError('La cantidad debe ser un número.')
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        raise ValueError('La cantidad debe ser un número.') from None
    if not value.is_finite():
        raise ValueError('La cantidad debe ser un número.')
    if value.as_tuple().exponent < -4:
        raise ValueError('Usa como máximo 4 decimales.')
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError('La cantidad no puede ser negativa.' if allow_zero else 'La cantidad debe ser mayor que cero.')
    if value > QUANTITY_MAX:
        raise ValueError('La cantidad es demasiado grande.')
    return value.quantize(_STEP)


@dataclass(frozen=True)
class OrderIngredient:
    product_id: UUID
    product_name: str
    unit_id: UUID | None
    unit_abbreviation: str | None
    quantity_per_preparation: Decimal
    actual_quantity: Decimal | None = None  # consumo real; solo existe tras pasar a refrigeración


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
    # Registro de producción (solo en REFRIGERATING).
    actual_output: Decimal | None = None
    entered_at: datetime | None = None
    refrigerated_at: datetime | None = None
    lot_id: UUID | None = None
    lot_code: str = ''
    cost_total: Decimal | None = None
    # Liberación del lote (solo en READY_TO_PACK).
    released_at: datetime | None = None
    released_by_id: UUID | None = None
    released_by_name: str = ''

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

    def validate_refrigeration(self, *, entered_at: object, actual_output: object, ingredients: object,
                               now: datetime) -> tuple[datetime, Decimal, dict[UUID, Decimal]]:
        """Normaliza y valida lo capturado (INV-02, INV-03); devuelve `(ingreso, elaborada, consumo por producto)`."""
        errors: dict = {}
        output = None
        try:
            output = parse_quantity(actual_output, allow_zero=False)
        except ValueError as exc:
            errors['actual_output'] = [str(exc)]
        if not isinstance(entered_at, datetime):
            errors['entered_at'] = ['La fecha y hora de ingreso es obligatoria.']
        elif entered_at.tzinfo is None:
            errors['entered_at'] = ['La fecha y hora de ingreso debe incluir zona horaria.']
        elif self.started_at is not None and entered_at < self.started_at:
            errors['entered_at'] = ['El ingreso no puede ser anterior al inicio de la preparación.']
        elif entered_at > now + CLOCK_TOLERANCE:
            errors['entered_at'] = ['El ingreso no puede estar en el futuro.']
        consumption: dict[UUID, Decimal] = {}
        expected = {line.product_id for line in self.ingredients}
        if not isinstance(ingredients, list):
            errors['ingredients'] = ['Indica el consumo real de cada ingrediente.']
        else:
            line_errors = []
            for item in ingredients:
                product_id = item.get('product_id') if isinstance(item, dict) else None
                try:
                    quantity = parse_quantity(item.get('actual_quantity') if isinstance(item, dict) else None,
                                              allow_zero=True)
                    if product_id not in expected or product_id in consumption:
                        raise ValueError('Ingrediente no válido para esta orden.')
                    consumption[product_id] = quantity
                    line_errors.append({})
                except ValueError as exc:
                    line_errors.append({'actual_quantity': [str(exc)]})
            if any(line_errors):
                errors['ingredients'] = line_errors
            elif set(consumption) != expected:
                errors['ingredients'] = ['Indica el consumo real de cada ingrediente.']
        if errors:
            raise OrderValidationError(errors)
        return entered_at, output, consumption

    def refrigerate(self, *, now: datetime, entered_at: datetime, actual_output: Decimal,
                    consumption: dict[UUID, Decimal], lot_id: UUID, lot_code: str,
                    cost_total: Decimal | None) -> None:
        """`IN_PREPARATION → REFRIGERATING` con lo realmente consumido y elaborado."""
        if self.status != OrderStatus.IN_PREPARATION:
            raise OrderStateError('La orden no está en preparación.')
        self.status = OrderStatus.REFRIGERATING
        self.actual_output = actual_output
        self.entered_at = entered_at
        self.refrigerated_at = now
        self.lot_id = lot_id
        self.lot_code = lot_code
        self.cost_total = cost_total
        self.ingredients = [OrderIngredient(line.product_id, line.product_name, line.unit_id, line.unit_abbreviation,
                                            line.quantity_per_preparation, consumption[line.product_id])
                            for line in self.ingredients]

    def releasable_from(self, min_hours: int) -> datetime | None:
        """Primera hora habilitada para liberar el lote: ingreso + mínimo (INV-02); `None` sin ingreso registrado."""
        if self.entered_at is None:
            return None
        return self.entered_at + timedelta(hours=min_hours)

    def release(self, *, now: datetime, min_hours: int, user_id: UUID | None, user_name: str) -> bool:
        """`REFRIGERATING → READY_TO_PACK` si ya se cumplió el mínimo (INV-01, INV-02, INV-06).

        Devuelve `False` sin cambios si ya estaba lista para empacar (INV-05).
        """
        if self.status == OrderStatus.READY_TO_PACK:
            return False
        if self.status != OrderStatus.REFRIGERATING:
            raise OrderStateError('La orden no está en refrigeración.')
        first = self.releasable_from(min_hours)
        if first is None or self.lot_id is None:
            raise OrderStateError('La orden no tiene un ingreso a refrigeración registrado.')
        if now < first:
            raise ReleaseTooEarly(first, min_hours)
        self.status = OrderStatus.READY_TO_PACK
        self.released_at = now
        self.released_by_id = user_id
        self.released_by_name = user_name
        return True
