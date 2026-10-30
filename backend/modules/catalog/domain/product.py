from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from .exceptions import ProductValidationError
from .unit import UnitOfMeasure

NAME_MAX_LENGTH = 150
PRICE_MAX = Decimal('9999999999.99')
CATEGORIES = ('raw_material', 'packaging', 'intermediate', 'finished', 'merchandise')
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


def validate_category(category: object) -> str:
    if not isinstance(category, str) or category not in CATEGORIES:
        raise _fail('category', 'La categoría debe ser una de: ' + ', '.join(CATEGORIES) + '.')
    return category


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
    # Solo obligatorio si el producto se puede vender (INV-02).
    sale_price: Decimal | None
    active: bool = True
    tracks_stock: bool = False
    base_unit_id: UUID | None = None
    # Resumen de lectura de la unidad base (lo completa la persistencia).
    base_unit: 'UnitSummary | None' = None
    # None solo en productos migrados sin clasificar (INV-01); la categoría no restringe los usos.
    category: str | None = None
    can_buy: bool = False
    can_sell: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def needs_review(self) -> bool:
        return self.category is None

    @classmethod
    def create(cls, name: object, sale_price: object = None, description: str | None = '', *,
               category: object = None, can_buy: object = False, can_sell: object = True) -> 'Product':
        errors: dict[str, list[str]] = {}
        product = cls(id=uuid4(), name='', description=(description or '').strip(), sale_price=None, active=True)
        for action in (lambda: product.rename(name), lambda: product.classify(category),
                       lambda: product.set_uses(can_buy, can_sell, sale_price)):
            try:
                action()
            except ProductValidationError as exc:
                errors.update(exc.errors)
        if errors:
            raise ProductValidationError(errors)
        return product

    def rename(self, name: object) -> None:
        self.name = validate_name(name)

    def describe(self, description: str | None) -> None:
        self.description = (description or '').strip()

    def change_price(self, sale_price: object) -> None:
        self.set_uses(self.can_buy, self.can_sell, sale_price)

    def classify(self, category: object) -> None:
        """Fija la categoría operativa; solo organiza y filtra, no cambia los usos."""
        self.category = validate_category(category)

    def set_uses(self, can_buy: object, can_sell: object, sale_price: object) -> None:
        """Fija si se compra y/o se vende junto con el precio resultante (obligatorio solo si se vende)."""
        errors: dict[str, list[str]] = {}
        for field, value in (('can_buy', can_buy), ('can_sell', can_sell)):
            if not isinstance(value, bool):
                errors[field] = ['Debe ser verdadero o falso.']
        price = None
        if sale_price is not None:
            try:
                price = validate_price(sale_price)
            except ProductValidationError as exc:
                errors.update(exc.errors)
        elif can_sell is True:
            errors['sale_price'] = ['El precio de venta es obligatorio para productos que se venden.']
        if errors:
            raise ProductValidationError(errors)
        self.can_buy, self.can_sell, self.sale_price = can_buy, can_sell, price

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
