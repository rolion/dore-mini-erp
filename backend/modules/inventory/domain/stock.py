from dataclasses import dataclass
from datetime import date
import re
from decimal import Decimal, InvalidOperation
from uuid import UUID

from .exceptions import OpeningValidationError

SOURCE_TYPE = 'inventory_opening'
REFERENCE_MAX_LENGTH = 100
QUANTITY_DECIMALS = Decimal('0.001')
QUANTITY_MAX = Decimal('99999999999.999')
# Solo texto decimal simple: sin signo, exponente ni dígitos no ASCII (igual que la validación de la interfaz).
_PLAIN_DECIMAL = re.compile(r'\d+(\.\d+)?', re.ASCII)


def _quantity_error(message: str) -> OpeningValidationError:
    return OpeningValidationError({'quantity': [message]})


def validate_quantity(value: object) -> Decimal:
    """Cantidad inicial: decimal no negativo con hasta 3 decimales. Nunca `float` (ni `bool`)."""
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise _quantity_error('La cantidad debe ser un número decimal.')
    if isinstance(value, str) and not _PLAIN_DECIMAL.fullmatch(value.strip()):
        if value.strip().startswith('-') and _PLAIN_DECIMAL.fullmatch(value.strip()[1:]):
            raise _quantity_error('La cantidad inicial no puede ser negativa.')
        raise _quantity_error('La cantidad debe ser un número decimal.')
    try:
        quantity = Decimal(value.strip() if isinstance(value, str) else value)
    except InvalidOperation:
        raise _quantity_error('La cantidad debe ser un número decimal.') from None
    if not quantity.is_finite():
        raise _quantity_error('La cantidad debe ser un número decimal.')
    if quantity < 0:
        raise _quantity_error('La cantidad inicial no puede ser negativa.')
    if quantity != quantity.quantize(QUANTITY_DECIMALS):
        raise _quantity_error('La cantidad admite como máximo 3 decimales.')
    quantity = quantity.quantize(QUANTITY_DECIMALS)
    if quantity > QUANTITY_MAX:
        raise _quantity_error(f'La cantidad no puede superar {QUANTITY_MAX}.')
    return quantity


def check_quantity_for_unit(quantity: Decimal, allows_fractions: bool) -> str | None:
    """Mensaje de error si la cantidad tiene fracción y la unidad base no la admite."""
    if not allows_fractions and quantity != quantity.to_integral_value():
        return 'La unidad base de este producto no admite fracciones.'
    return None


@dataclass(frozen=True)
class OpeningLine:
    product_id: UUID
    quantity: Decimal


@dataclass(frozen=True)
class StockOpening:
    """Carga única de existencias iniciales de varios productos en un almacén (INV-01, INV-02).

    `opening_id` es la clave que genera el cliente: reenviarla no duplica la apertura.
    """

    opening_id: UUID
    warehouse_id: UUID
    movement_date: date
    reference: str
    lines: tuple[OpeningLine, ...]

    @classmethod
    def create(cls, opening_id: UUID, warehouse_id: UUID, movement_date: date, reference: object,
               lines: list[tuple[UUID, object]], today: date) -> 'StockOpening':
        errors: dict[str, object] = {}
        if not isinstance(reference, str) or not reference.strip():
            errors['reference'] = ['La referencia de apertura es obligatoria.']
        elif len(reference.strip()) > REFERENCE_MAX_LENGTH:
            errors['reference'] = [f'La referencia no puede superar {REFERENCE_MAX_LENGTH} caracteres.']
        if movement_date > today:
            errors['movement_date'] = ['La fecha de apertura no puede ser futura.']
        if not lines:
            errors['lines'] = [{'non_field_errors': ['Agrega al menos un producto.']}]
        else:
            line_errors: list[dict[str, list[str]]] = []
            validated: list[OpeningLine] = []
            seen: set[UUID] = set()
            for product_id, raw_quantity in lines:
                line_error: dict[str, list[str]] = {}
                quantity = Decimal(0)
                try:
                    quantity = validate_quantity(raw_quantity)
                except OpeningValidationError as exc:
                    line_error.update(exc.errors)
                if product_id in seen:
                    line_error['product_id'] = ['El producto está repetido en la apertura.']
                seen.add(product_id)
                line_errors.append(line_error)
                validated.append(OpeningLine(product_id, quantity))
            if any(line_errors):
                errors['lines'] = line_errors
        if errors:
            raise OpeningValidationError(errors)
        return cls(opening_id, warehouse_id, movement_date, reference.strip(), tuple(validated))

    @property
    def recorded_lines(self) -> tuple[OpeningLine, ...]:
        """Líneas que generan movimiento: el libro exige cantidad > 0, así que las de cantidad 0 no se registran."""
        return tuple(line for line in self.lines if line.quantity > 0)


@dataclass(frozen=True)
class StockBalanceEntry:
    product_id: UUID
    warehouse_id: UUID
    warehouse_name: str
    quantity: Decimal
