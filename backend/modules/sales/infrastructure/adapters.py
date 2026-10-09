"""Adaptadores de los puertos de Sales sobre las fachadas públicas de otros módulos y el reloj de Django.

Es el único lugar de Sales que conoce a Catalog y Customers, y solo por sus `services.py`.
"""
from collections.abc import Iterable
from datetime import date, datetime
from uuid import UUID

from django.utils import timezone

from modules.catalog import services as catalog_services
from modules.customers import services as customer_services
from modules.sales.application.ports import CustomerInfo, ProductInfo


class ProductCatalogAdapter:
    def get_product_for_sale(self, product_id: UUID) -> ProductInfo | None:
        product = catalog_services.get_product_for_sale(product_id)
        if product is None:
            return None
        return ProductInfo(id=product.id, name=product.name, sale_price=product.sale_price, active=product.active)


class CustomerDirectoryAdapter:
    def get_customer_for_sale(self, customer_id: UUID) -> CustomerInfo | None:
        customer = customer_services.get_customer_for_sale(customer_id)
        if customer is None:
            return None
        return CustomerInfo(id=customer.id, name=customer.name, active=customer.active)

    def get_customer_names(self, customer_ids: Iterable[UUID]) -> dict[UUID, str]:
        return customer_services.get_customer_names(customer_ids)


class SystemClock:
    """"Hoy" según la zona horaria configurada (`TIME_ZONE`), no la del navegador."""

    def today(self) -> date:
        return timezone.localdate()

    def now(self) -> datetime:
        return timezone.now()
