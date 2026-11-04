"""Puente de Cotizaciones hacia las fachadas públicas de Servicios y Clientes."""
from uuid import UUID

from modules.customers.services import CustomerForSale, get_customer_for_sale
from modules.service_catalog.services import ServiceSnapshot, get_service_for_new_use


class ServiceLookup:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def for_new_use(self, service_id: UUID) -> ServiceSnapshot | None:
        return get_service_for_new_use(self.company_id, service_id)


class CustomerLookup:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get(self, customer_id: UUID) -> CustomerForSale | None:
        return get_customer_for_sale(self.company_id, customer_id)
