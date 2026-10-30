from collections.abc import Callable
from uuid import UUID

from modules.catalog.domain.exceptions import (
    ProductNotFound,
    ProductValidationError,
    StockHistoryLocked,
    UnitNotFound,
)
from modules.catalog.domain.product import Product
from modules.catalog.domain.repositories import ProductRepository, UnitRepository
from modules.catalog.domain.unit import UnitOfMeasure

UNSET = object()

INVENTORY_DISABLED_MESSAGE = 'Habilita el módulo Inventario para controlar stock.'


class StockControl:
    """Aplica el control de stock y la unidad base de un producto (INV-01, INV-02, INV-08).

    `inventory_enabled` indica si la empresa tiene Inventario habilitado; `has_history` consulta si el producto
    tiene movimientos previos (puerto neutro `shared.stock_history`).
    """

    def __init__(self, units: UnitRepository, inventory_enabled: bool = True,
                 has_history: Callable[[UUID], bool] = lambda product_id: False):
        self.units = units
        self.inventory_enabled = inventory_enabled
        self.has_history = has_history

    def apply(self, product: Product, tracks_stock: object = UNSET, base_unit_id: object = UNSET,
              *, is_new: bool = False) -> bool:
        """Devuelve si cambió algo. Sin cambios efectivos no valida nada (EDGE-03, EDGE-06)."""
        if tracks_stock is UNSET and base_unit_id is UNSET:
            return False
        if tracks_stock is not UNSET and not isinstance(tracks_stock, bool):
            raise ProductValidationError({'tracks_stock': ['Debe ser verdadero o falso.']})
        new_tracks = product.tracks_stock if tracks_stock is UNSET else tracks_stock
        new_unit_id = None if not new_tracks else (product.base_unit_id if base_unit_id is UNSET else base_unit_id)
        if (new_tracks, new_unit_id) == (product.tracks_stock, product.base_unit_id):
            return False
        if new_tracks and not self.inventory_enabled:
            raise ProductValidationError({'tracks_stock': [INVENTORY_DISABLED_MESSAGE]})
        if not is_new and self.has_history(product.id):
            raise StockHistoryLocked()
        unit = self._unit(new_unit_id) if new_tracks and new_unit_id is not None else None
        product.configure_stock(new_tracks, unit)
        return True

    def _unit(self, unit_id: UUID) -> UnitOfMeasure:
        unit = self.units.get(unit_id)
        if unit is None:
            raise ProductValidationError({'base_unit_id': ['La unidad base no existe.']})
        return unit


class CreateProduct:
    def __init__(self, repository: ProductRepository, stock: StockControl | None = None):
        self.repository = repository
        self.stock = stock

    def execute(self, name: object, sale_price: object = None, description: str = '', category: object = None,
                can_buy: object = False, can_sell: object = True,
                tracks_stock: object = UNSET, base_unit_id: object = UNSET) -> Product:
        product = Product.create(name=name, sale_price=sale_price, description=description,
                                 category=category, can_buy=can_buy, can_sell=can_sell)
        if self.stock is not None:
            self.stock.apply(product, tracks_stock, base_unit_id, is_new=True)
        return self.repository.save(product)


class UpdateProduct:
    """Edición parcial de datos comerciales; el estado (`active`) no se cambia por aquí."""

    def __init__(self, repository: ProductRepository, stock: StockControl | None = None):
        self.repository = repository
        self.stock = stock

    def execute(self, product_id: UUID, name: object = UNSET, description: object = UNSET,
                sale_price: object = UNSET, tracks_stock: object = UNSET, base_unit_id: object = UNSET,
                category: object = UNSET, can_buy: object = UNSET, can_sell: object = UNSET) -> Product:
        product = self.repository.get(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        errors: dict[str, list[str]] = {}
        changes = (
            (name, product.rename),
            (description, product.describe),
            (category, product.classify),
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
        if any(value is not UNSET for value in (can_buy, can_sell, sale_price)):
            try:
                product.set_uses(
                    product.can_buy if can_buy is UNSET else can_buy,
                    product.can_sell if can_sell is UNSET else can_sell,
                    product.sale_price if sale_price is UNSET else sale_price)
                changed = True
            except ProductValidationError as exc:
                errors.update(exc.errors)
        if self.stock is not None:
            try:
                changed = self.stock.apply(product, tracks_stock, base_unit_id) or changed
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


class CreateUnit:
    def __init__(self, repository: UnitRepository):
        self.repository = repository

    def execute(self, name: object, abbreviation: object, allows_fractions: bool = False) -> UnitOfMeasure:
        unit = UnitOfMeasure.create(name=name, abbreviation=abbreviation, allows_fractions=allows_fractions)
        return self.repository.save(unit)


class UpdateUnit:
    """Redefine la unidad; si está en uso solo se acepta lo que no cambia su significado."""

    def __init__(self, repository: UnitRepository):
        self.repository = repository

    def execute(self, unit_id: UUID, name: object = UNSET, abbreviation: object = UNSET,
                allows_fractions: object = UNSET) -> UnitOfMeasure:
        unit = self.repository.get(unit_id)
        if unit is None:
            raise UnitNotFound(unit_id)
        changed = unit.redefine(
            unit.name if name is UNSET else name,
            unit.abbreviation if abbreviation is UNSET else abbreviation,
            unit.allows_fractions if allows_fractions is UNSET else allows_fractions,
        )
        return self.repository.save(unit) if changed else unit


class SetUnitActive:
    def __init__(self, repository: UnitRepository, active: bool):
        self.repository = repository
        self.active = active

    def execute(self, unit_id: UUID) -> UnitOfMeasure:
        unit = self.repository.get(unit_id)
        if unit is None:
            raise UnitNotFound(unit_id)
        unit.activate() if self.active else unit.deactivate()
        return self.repository.save(unit)

