"""Adaptadores de los puertos de Inventario sobre las fachadas públicas de otros módulos.

Es el único lugar de Inventario que conoce a Catalog y Modularity, y solo por sus `services.py`.
"""
from collections.abc import Iterable
from uuid import UUID

from modules.catalog import services as catalog_services
from modules.inventory.application.movement_ports import ProductInfo
from modules.inventory.domain.exceptions import MovementConflict, MovementValidationError
from modules.modularity import services as modularity_services
from shared import stock_valuation


def _info(p) -> ProductInfo:
    return ProductInfo(
        id=p.id, name=p.name, tracks_stock=p.tracks_stock, unit_abbreviation=p.unit_abbreviation,
        allows_fractions=p.allows_fractions, active=p.active,
        category=p.category, can_buy=p.can_buy, can_sell=p.can_sell)


class CatalogProductDirectory:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get_products(self, product_ids: Iterable[UUID]) -> dict[UUID, ProductInfo]:
        found = catalog_services.get_products_for_inventory(self.company_id, product_ids)
        return {product_id: _info(p) for product_id, p in found.items()}

    def list_stock_products(self, search: str | None = None, active: bool | None = None,
                            category: str | None = None, can_buy: bool | None = None,
                            can_sell: bool | None = None) -> list[ProductInfo]:
        return [_info(p) for p in catalog_services.list_products_for_inventory(
            self.company_id, search=search, active=active, category=category, can_buy=can_buy, can_sell=can_sell)]


class ModularityInventoryPolicy:
    """Política de inventario de la empresa, leída de su configuración en cada consulta (sin caché)."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def allow_negative_stock(self) -> bool:
        if stock_valuation.is_valued(self.company_id):  # inventario valorado: nunca hay saldos negativos
            return False
        return modularity_services.get_inventory_settings(self.company_id).allow_negative_stock

    def value_movement(self, movement, value: stock_valuation.MovementValue | None = None) -> None:
        """Valora el movimiento con Costeo (si la empresa tiene inventario valorado) o lo rechaza con un motivo."""
        if not stock_valuation.is_valued(self.company_id):
            return
        source = movement.source
        try:
            stock_valuation.value_movement(self.company_id, stock_valuation.MovementToValue(
                movement_id=movement.id, product_id=movement.product_id, warehouse_id=movement.warehouse_id,
                kind=movement.kind.value, quantity=movement.quantity, occurred_at=movement.occurred_at,
                source_type=source.type if source else None, source_id=source.id if source else '',
                reverses_id=movement.reverses_id, value=value))
        except stock_valuation.ValuationRejected as exc:
            if exc.code == 'valuation_blocked':
                raise MovementConflict(exc.code, exc.message) from exc
            raise MovementValidationError({exc.field: [exc.message]}) from exc
