"""Fachada pública del módulo Customers para otros módulos (p. ej. Sales).

Es la única vía de entrada entre módulos: devuelve DTO inmutables, nunca entidades ni modelos.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from modules.customers.infrastructure.django.models import CustomerModel
from modules.customers.infrastructure.django.repositories import DjangoCustomerRepository


@dataclass(frozen=True)
class CustomerForSale:
    id: UUID
    name: str
    active: bool


def get_customer_for_sale(customer_id: UUID) -> CustomerForSale | None:
    """El cliente con su estado vigente, o `None` si no existe.

    La regla de "cliente activo" la aplica quien vende, no la fachada.
    """
    customer = DjangoCustomerRepository().get(customer_id)
    if customer is None:
        return None
    return CustomerForSale(id=customer.id, name=customer.name, active=customer.active)


def get_customer_names(customer_ids: Iterable[UUID]) -> dict[UUID, str]:
    """Nombres vigentes de varios clientes en una sola consulta; los ids inexistentes no aparecen."""
    ids = set(customer_ids)
    if not ids:
        return {}
    return dict(CustomerModel.objects.filter(pk__in=ids).values_list('id', 'name'))
