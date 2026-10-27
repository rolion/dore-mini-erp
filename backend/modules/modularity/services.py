"""Fachada pública de solo lectura de la configuración de la empresa (convención de `docs/architecture/ddd.md`).

La consumen otros módulos (hoy Sales) a través de su adaptador; devuelve DTO inmutables, nunca modelos.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from modules.modularity.domain import settings as domain
from modules.modularity.infrastructure.django.repositories import DjangoCompanySettingRepository


@dataclass(frozen=True)
class SalesSettings:
    default_sales_channel: str
    default_payment_method: str
    max_discount_percent: Decimal


def get_sales_settings(company_id: UUID) -> SalesSettings:
    stored = DjangoCompanySettingRepository(company_id).values()

    def value(key: str) -> str:
        return stored.get(key, domain.BY_SETTING_KEY[key].default)

    return SalesSettings(
        default_sales_channel=value('sales.default_sales_channel'),
        default_payment_method=value('sales.default_payment_method'),
        max_discount_percent=Decimal(value('sales.max_discount_percent')),
    )
