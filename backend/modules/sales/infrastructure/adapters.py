"""Adaptadores de los puertos de Sales sobre las fachadas públicas de otros módulos y el reloj de Django.

Es el único lugar de Sales que conoce a Catalog, Customers y Modularity, y solo por sus `services.py`.
"""
import logging
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.utils import timezone

from modules.catalog import services as catalog_services
from modules.customers import services as customer_services
from modules.modularity import services as modularity_services
from modules.sales.application.ports import CustomerInfo, ProductInfo
from modules.sales.domain.order import MAX_DISCOUNT_PERCENT

logger = logging.getLogger(__name__)


class ProductCatalogAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get_product_for_sale(self, product_id: UUID) -> ProductInfo | None:
        product = catalog_services.get_product_for_sale(self.company_id, product_id)
        if product is None:
            return None
        return ProductInfo(id=product.id, name=product.name, sale_price=product.sale_price, active=product.active)


class CustomerDirectoryAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get_customer_for_sale(self, customer_id: UUID) -> CustomerInfo | None:
        customer = customer_services.get_customer_for_sale(self.company_id, customer_id)
        if customer is None:
            return None
        return CustomerInfo(id=customer.id, name=customer.name, active=customer.active)

    def get_customer_names(self, customer_ids: Iterable[UUID]) -> dict[UUID, str]:
        return customer_services.get_customer_names(self.company_id, customer_ids)


class SalesSettingsAdapter:
    """Configuración de Ventas de la empresa; si no se puede leer, rige el valor inicial (regla previa)."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def max_discount_percent(self) -> Decimal:
        try:
            return modularity_services.get_sales_settings(self.company_id).max_discount_percent
        except Exception:
            logger.exception('No se pudo leer la configuración de Ventas; se usa el valor inicial.')
            return MAX_DISCOUNT_PERCENT


class SystemClock:
    """"Hoy" según la zona horaria configurada (`TIME_ZONE`), no la del navegador."""

    def today(self) -> date:
        return timezone.localdate()

    def now(self) -> datetime:
        return timezone.now()
