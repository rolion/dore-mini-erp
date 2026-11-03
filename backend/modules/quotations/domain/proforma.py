"""Agregado Proforma (puro: sin Django). Dinero siempre en `Decimal`, a dos decimales."""
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

CURRENCY = 'BOB'
DRAFT, PRESENTED, SUPERSEDED = 'draft', 'presented', 'superseded'
STATUSES = (DRAFT, PRESENTED, SUPERSEDED)
MAX_LINES = 200
MAX_QUANTITY = Decimal('9999.99')
MAX_PRICE = Decimal('9999999999.99')
MAX_NOTES = 2000
_CENTS = Decimal('0.01')


class ProformaValidationError(Exception):
    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(errors)


class ProformaNotFound(Exception):
    pass


class ProformaStateError(Exception):
    """Operación no permitida para el estado actual (se traduce a 409)."""


def money(value: Decimal) -> Decimal:
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


def _has_cents_only(value: Decimal) -> bool:
    return value.is_finite() and value == value.quantize(_CENTS)


def line_errors(quantity: Decimal | None, unit_price: Decimal | None) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if quantity is None or not _has_cents_only(quantity) or quantity <= 0 or quantity > MAX_QUANTITY:
        errors['quantity'] = ['Ingresa una cantidad mayor que cero (máximo 9999.99, dos decimales).']
    if unit_price is None or not _has_cents_only(unit_price) or unit_price < 0 or unit_price > MAX_PRICE:
        errors['unit_price'] = ['Ingresa un precio igual o mayor que cero con dos decimales.']
    return errors


@dataclass(frozen=True)
class ProformaLine:
    """Línea con nombre y precio congelados al incorporar el servicio."""
    id: UUID
    service_id: UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    treatment_item_id: UUID | None = None  # reservado: no existe aún el módulo de tratamientos
    piece: str = ''

    @property
    def subtotal(self) -> Decimal:
        return money(self.quantity * self.unit_price)


@dataclass
class Proforma:
    id: UUID
    number: str
    version: int
    status: str
    customer_id: UUID
    customer_name: str
    date: date
    valid_until: date | None = None
    notes: str = ''
    lines: list[ProformaLine] = field(default_factory=list)
    created_by: int | None = None

    currency = CURRENCY

    @property
    def total(self) -> Decimal:
        return money(sum((line.subtotal for line in self.lines), Decimal('0')))

    @classmethod
    def create(cls, *, number: str, customer_id: UUID, customer_name: str, date: date,
               valid_until: date | None = None, notes: str = '', lines=(), created_by: int | None = None):
        proforma = cls(uuid4(), number, 1, DRAFT, customer_id, customer_name, date, created_by=created_by)
        proforma.replace_content(customer_id=customer_id, customer_name=customer_name, date=date,
                                 valid_until=valid_until, notes=notes, lines=lines)
        return proforma

    def replace_content(self, *, customer_id: UUID, customer_name: str, date: date,
                        valid_until: date | None, notes: str, lines) -> None:
        if self.status != DRAFT:
            raise ProformaStateError('Solo se puede editar una proforma en borrador.')
        lines = list(lines)
        errors: dict = {}
        if valid_until is not None and valid_until < date:
            errors['valid_until'] = ['La vigencia no puede ser anterior a la fecha.']
        if len(notes) > MAX_NOTES:
            errors['notes'] = [f'Máximo {MAX_NOTES} caracteres.']
        if len(lines) > MAX_LINES:
            errors['lines'] = [f'Máximo {MAX_LINES} líneas.']
        else:
            per_line = [line_errors(line.quantity, line.unit_price) for line in lines]
            if any(per_line):
                errors['lines'] = per_line
        if errors:
            raise ProformaValidationError(errors)
        self.customer_id, self.customer_name, self.date = customer_id, customer_name, date
        self.valid_until, self.notes, self.lines = valid_until, notes, lines

    def present(self) -> None:
        if self.status != DRAFT:
            raise ProformaStateError('Solo se puede presentar una proforma en borrador.')
        if not self.lines:
            raise ProformaValidationError({'lines': ['Agrega al menos una línea para presentar la proforma.']})
        self.status = PRESENTED

    def supersede(self) -> None:
        if self.status != PRESENTED:
            raise ProformaStateError('Solo una proforma presentada puede ser reemplazada.')
        self.status = SUPERSEDED

    def new_version(self) -> 'Proforma':
        """Borrador `version + 1` con las líneas ya congeladas (no se relee el catálogo)."""
        if self.status != PRESENTED:
            raise ProformaStateError('Solo se puede crear una versión nueva desde una proforma presentada.')
        copied = [replace(line, id=uuid4()) for line in self.lines]
        return Proforma(uuid4(), self.number, self.version + 1, DRAFT, self.customer_id, self.customer_name,
                        self.date, self.valid_until, self.notes, copied, self.created_by)
