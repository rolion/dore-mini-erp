"""Fachada pública del módulo Customers para otros módulos (p. ej. Sales).

Es la única vía de entrada entre módulos: devuelve DTO inmutables, nunca entidades ni modelos.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from modules.customers.infrastructure.django.models import CustomerModel
from modules.customers.infrastructure.django.repositories import DjangoCustomerRepository
from modules.customers.infrastructure.django.demographics import CustomerDemographicsModel


@dataclass(frozen=True)
class CustomerForSale:
    id: UUID
    name: str
    active: bool


def get_customer_for_sale(company_id: UUID, customer_id: UUID) -> CustomerForSale | None:
    """El cliente de la empresa con su estado vigente, o `None` si no existe (o es de otra empresa).

    La regla de "cliente activo" la aplica quien vende, no la fachada.
    """
    customer = DjangoCustomerRepository(company_id).get(customer_id)
    if customer is None:
        return None
    return CustomerForSale(id=customer.id, name=customer.name, active=customer.active)


def get_customer_names(company_id: UUID, customer_ids: Iterable[UUID]) -> dict[UUID, str]:
    """Nombres vigentes de varios clientes de la empresa en una sola consulta; los ids inexistentes no aparecen."""
    ids = set(customer_ids)
    if not ids:
        return {}
    return dict(CustomerModel.objects.filter(company_id=company_id, pk__in=ids).values_list('id', 'name'))


@dataclass(frozen=True)
class CustomerAdministrative:
    id: UUID
    name: str
    phone: str
    email: str
    active: bool
    birth_date: str | None
    responsible_name: str
    responsible_phone: str


def get_customers_administrative(company_id: UUID, customer_ids: Iterable[UUID]) -> dict[UUID, CustomerAdministrative]:
    """Administrative data only, in two bounded queries; never returns clinical information."""
    ids = set(customer_ids)
    demographics = {r.customer_id: r for r in CustomerDemographicsModel.objects.filter(
        company_id=company_id, customer_id__in=ids)}
    result = {}
    for row in CustomerModel.objects.filter(company_id=company_id, id__in=ids):
        demo = demographics.get(row.id)
        result[row.id] = CustomerAdministrative(
            row.id, row.name, row.phone, row.email, row.active,
            demo.birth_date.isoformat() if demo and demo.birth_date else None,
            demo.responsible_name if demo else '', demo.responsible_phone if demo else '')
    return result


def search_customer_ids(company_id: UUID, search: str) -> list[UUID]:
    """Identity values only; never exposes a model or queryset across contexts."""
    return [customer.id for customer in DjangoCustomerRepository(company_id).list(search=search)]
