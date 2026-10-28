from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from .exceptions import ProductValidationError
from .unit import UnitOfMeasure

NAME_MAX_LENGTH = 150
PRICE_MAX = Decimal('9999999999.99')
_CENTS = Decimal('0.01')


def _fail(field: str, message: str) -> ProductValidationError:
    return ProductValidationError({field: [message]})


def validate_name(name: object) -> str:
    if not isinstance(name, str) or not name.strip():
        raise _fail('name', 'El nombre es obligatorio.')
    name = name.strip()
    if len(name) > NAME_MAX_LENGTH:
        raise _fail('name', f'El nombre no puede superar {NAME_MAX_LENGTH} caracteres.')
    return name


def validate_price(value: object) -> Decimal:
    # float y bool quedan fuera: el dinero nunca se maneja como float.
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise _fail('sale_price', 'El precio de venta debe ser un número decimal.')
    try:
        price = Decimal(value.strip() if isinstance(value, str) else value)
    except InvalidOperation:
        raise _fail('sale_price', 'El precio de venta debe ser un número decimal.') from None
    if not price.is_finite():
        raise _fail('sale_price', 'El precio de venta debe ser un número decimal.')
    if price < 0:
        raise _fail('sale_price', 'El precio de venta no puede ser negativo.')
    if price != price.quantize(_CENTS):
        raise _fail('sale_price', 'El precio de venta admite como máximo 2 decimales.')
    price = price.quantize(_CENTS)
    if price > PRICE_MAX:
        raise _fail('sale_price', f'El precio de venta no puede superar {PRICE_MAX}.')
    return price


@dataclass(frozen=True)
class UnitSummary:
    id: UUID
    name: str
    abbreviation: str
    allows_fractions: bool = False


@dataclass
class Product:
    id: UUID
    name: str
    description: str
    sale_price: Decimal
    active: bool = True
    tracks_stock: bool = False
    base_unit_id: UUID | None = None
    # Resumen de lectura de la unidad base (lo completa la persistencia).
    base_unit: 'UnitSummary | None' = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, name: object, sale_price: object, description: str | None = '') -> 'Product':
        errors: dict[str, list[str]] = {}
        validated: dict[str, object] = {}
        for field, validator, raw in (('name', validate_name, name), ('sale_price', validate_price, sale_price)):
            try:
                validated[field] = validator(raw)
            except ProductValidationError as exc:
                errors.update(exc.errors)
        if errors:
            raise ProductValidationError(errors)
        return cls(
            id=uuid4(),
            name=validated['name'],
            description=(description or '').strip(),
            sale_price=validated['sale_price'],
            active=True,
        )

    def rename(self, name: object) -> None:
        self.name = validate_name(name)

    def describe(self, description: str | None) -> None:
        self.description = (description or '').strip()

    def change_price(self, sale_price: object) -> None:
        self.sale_price = validate_price(sale_price)

    def configure_stock(self, tracks_stock: bool, base_unit: 'UnitOfMeasure | None') -> None:
        """Activa o desactiva el control de stock; al controlarlo exige una unidad base activa."""
        if not tracks_stock:
            self.tracks_stock, self.base_unit_id, self.base_unit = False, None, None
            return
        if base_unit is None:
            raise _fail('base_unit_id', 'La unidad base es obligatoria cuando el producto controla stock.')
        if not base_unit.active and base_unit.id != self.base_unit_id:
            raise _fail('base_unit_id', 'La unidad base debe estar activa.')
        self.tracks_stock, self.base_unit_id = True, base_unit.id
        self.base_unit = UnitSummary(
            base_unit.id, base_unit.name, base_unit.abbreviation, base_unit.allows_fractions)

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        self.active = False
