"""Valoración inicial de inventario (puro: sin Django).

Método fijo: promedio ponderado móvil por producto y empresa, como costo de gestión (no política fiscal ni contable).
La adopción es un corte inmutable: se crea una vez con `ValuationAdoption.adopt` y no tiene mutadores.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from uuid import UUID

from .exceptions import ValuationValidationError

METHOD = 'weighted_moving_average'
MONEY_STEP = Decimal('0.01')
QUANTITY_STEP = Decimal('0.0001')
UNIT_COST_STEP = Decimal('0.000001')
TOTAL_MAX = Decimal('99999999999999.99')
QUANTITY_MAX = Decimal('99999999999.9999')
SOURCE_MAX_LENGTH = 200
DEFAULT_SOURCE = 'Ingreso manual'
# Solo texto decimal simple: sin signo, exponente ni dígitos no ASCII.
_PLAIN_DECIMAL = re.compile(r'\d+(\.\d+)?', re.ASCII)

PENDING_MESSAGE = 'Pendiente: ingrese un valor o declare costo cero.'


def compute_unit_cost(total_value: Decimal, quantity: Decimal) -> Decimal:
    """Costo unitario derivado: valor total ÷ cantidad, a 6 decimales con `ROUND_HALF_UP`."""
    return (total_value / quantity).quantize(UNIT_COST_STEP, rounding=ROUND_HALF_UP)


def _parse_decimal(raw: object) -> Decimal | None:
    """Decimal desde `str`/`int`/`Decimal` (nunca `float` ni `bool`); `None` si no es un decimal simple no negativo."""
    if isinstance(raw, bool) or not isinstance(raw, (Decimal, int, str)):
        return None
    if isinstance(raw, str):
        text = raw.strip()
        if not _PLAIN_DECIMAL.fullmatch(text):
            return None
        raw = text
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    return value if value.is_finite() and value >= 0 else None


def parse_quantity(raw: object) -> Decimal:
    value = _parse_decimal(raw)
    if value is None:
        raise ValuationValidationError({'reconciled_quantity': ['La cantidad debe ser un número decimal.']})
    if value != value.quantize(QUANTITY_STEP):
        raise ValuationValidationError({'reconciled_quantity': ['La cantidad admite como máximo 4 decimales.']})
    value = value.quantize(QUANTITY_STEP)
    if value <= 0 or value > QUANTITY_MAX:
        raise ValuationValidationError({'reconciled_quantity': ['La cantidad conciliada debe ser mayor que cero.']})
    return value


def parse_total_value(raw: object) -> Decimal | None:
    """Valor total en BOB; `None` si falta (Pendiente). Lanza si no es un importe válido."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    value = _parse_decimal(raw)
    if value is None:
        raise ValuationValidationError({'total_value': ['El valor debe ser un importe decimal no negativo.']})
    if value != value.quantize(MONEY_STEP):
        raise ValuationValidationError({'total_value': ['El valor admite como máximo 2 decimales.']})
    value = value.quantize(MONEY_STEP)
    if value > TOTAL_MAX:
        raise ValuationValidationError({'total_value': [f'El valor no puede superar {TOTAL_MAX}.']})
    return value


@dataclass(frozen=True)
class ValuationLine:
    product_id: UUID
    reconciled_quantity: Decimal
    total_value: Decimal
    unit_cost: Decimal
    declared_zero: bool
    source: str

    @classmethod
    def create(cls, product_id: UUID, reconciled_quantity: object, total_value: object, declared_zero: object,
               source: object) -> 'ValuationLine':
        errors: dict[str, list[str]] = {}
        quantity = Decimal(0)
        value: Decimal | None = None
        try:
            quantity = parse_quantity(reconciled_quantity)
        except ValuationValidationError as exc:
            errors.update(exc.errors)  # type: ignore[arg-type]
        try:
            value = parse_total_value(total_value)
        except ValuationValidationError as exc:
            errors.update(exc.errors)  # type: ignore[arg-type]
        if declared_zero not in (None, True, False):
            errors['declared_zero'] = ['Debe ser verdadero o falso.']
        zero = declared_zero is True
        if 'total_value' not in errors:
            if zero:
                if value not in (None, Decimal('0.00')):
                    errors['total_value'] = ['Un costo cero declarado no admite un valor distinto de cero.']
                value = Decimal('0.00')
            elif value is None:
                errors['total_value'] = [PENDING_MESSAGE]
            elif value == 0:
                errors['total_value'] = ['Un costo cero debe declararse explícitamente.']
        text = DEFAULT_SOURCE if source is None or (isinstance(source, str) and not source.strip()) else source
        if not isinstance(text, str):
            errors['source'] = ['La fuente debe ser texto.']
        elif len(text.strip()) > SOURCE_MAX_LENGTH:
            errors['source'] = [f'La fuente no puede superar {SOURCE_MAX_LENGTH} caracteres.']
        if errors:
            raise ValuationValidationError(errors)
        assert value is not None and isinstance(text, str)
        return cls(product_id, quantity, value, compute_unit_cost(value, quantity), zero, text.strip())


def parse_lines(raw_lines: list[dict]) -> list[ValuationLine]:
    """Valida todas las líneas enviadas; si alguna falla lanza un solo error con un dict por línea."""
    line_errors: list[dict[str, list[str]]] = []
    lines: list[ValuationLine] = []
    seen: set[UUID] = set()
    for raw in raw_lines:
        product_id = raw['product_id']
        errors: dict[str, list[str]] = {}
        try:
            lines.append(ValuationLine.create(
                product_id, raw.get('reconciled_quantity'), raw.get('total_value'), raw.get('declared_zero'),
                raw.get('source')))
        except ValuationValidationError as exc:
            errors = dict(exc.errors)  # type: ignore[arg-type]
        if product_id in seen:
            errors = {**errors, 'product_id': ['El producto está repetido en la valoración.']}
        seen.add(product_id)
        line_errors.append(errors)
    if any(line_errors):
        raise ValuationValidationError({'lines': line_errors})
    return lines


def _content_key(line: ValuationLine) -> tuple:
    return (line.product_id, line.reconciled_quantity, line.total_value, line.declared_zero, line.source)


@dataclass(frozen=True)
class ValuationAdoption:
    """Base monetaria inicial de la empresa: una por empresa y de solo lectura."""

    id: UUID
    cutoff_at: datetime
    method: str
    user_id: UUID | None
    user_name: str
    lines: tuple[ValuationLine, ...]

    @classmethod
    def adopt(cls, adoption_id: UUID, cutoff_at: datetime, user_id: UUID | None, user_name: str,
              lines: list[ValuationLine]) -> 'ValuationAdoption':
        ordered = tuple(sorted(lines, key=lambda line: str(line.product_id)))
        return cls(adoption_id, cutoff_at, METHOD, user_id, user_name, ordered)

    def same_content_as(self, lines: list[ValuationLine]) -> bool:
        """Réplica idempotente: mismas líneas (producto, cantidad, valor, cero declarado y fuente)."""
        return len(self.lines) == len(lines) and {_content_key(line) for line in self.lines} == {
            _content_key(line) for line in lines}
