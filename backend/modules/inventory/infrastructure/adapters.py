"""Adaptadores de los puertos de Inventario sobre las fachadas públicas de otros módulos.

Es el único lugar de Inventario que conoce a Catalog, Modularity y Accounting, y solo por sus `services.py`.
"""
from collections.abc import Iterable
from datetime import date
from uuid import UUID

from modules.accounting import services as accounting_services
from modules.catalog import services as catalog_services
from modules.inventory.application.movement_ports import ProductInfo
from modules.inventory.domain.exceptions import LotNumberingRejected
from modules.inventory.domain.lot import LotNumber
from modules.inventory.infrastructure.django.models import LotNumberCounterModel
from modules.modularity import services as modularity_services
from shared.fiscal_numbering import allocate_period_number


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
        return modularity_services.get_inventory_settings(self.company_id).allow_negative_stock


class LotNumberingAdapter:
    """Serie de lotes por período fiscal (ADR lotes): bloquea el período y su contador en la transacción del lote."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def next_number(self, lot_date: date) -> LotNumber:
        try:
            period, number = allocate_period_number(self.company_id, lot_date, LotNumberCounterModel)
        except accounting_services.DateOutsideFiscalPeriod:
            raise LotNumberingRejected(
                'fiscal_period_missing',
                f'La fecha del lote ({lot_date.isoformat()}) no está dentro de ningún período fiscal. '
                'Cree el período en Contabilidad para poder crear el lote.') from None
        except accounting_services.FiscalPeriodClosed as exc:
            raise LotNumberingRejected(
                'fiscal_period_closed',
                f'El período fiscal «{exc.name}» está cerrado: no se puede crear un lote con fecha '
                f'{lot_date.isoformat()}. Reabra el período en Contabilidad.', {'period': exc.name}) from None
        return LotNumber(period.id, period.name, number)
