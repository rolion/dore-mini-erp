"""Fachada pública del módulo Customers para otros módulos (p. ej. Sales).

Es la única vía de entrada entre módulos: devuelve DTO inmutables, nunca entidades ni modelos.
"""
from collections.abc import Collection, Iterable
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


@dataclass(frozen=True)
class CustomerForCrm:
    id: UUID
    name: str
    phone: str


class CrmCustomerList:
    """Clientes activos paginables sin cargarlos todos: `count()` y rebanadas devuelven DTO de solo lectura."""

    def __init__(self, customers):
        self._customers = customers

    def count(self) -> int:
        return self._customers.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [CustomerForCrm(c.id, c.name, c.phone) for c in self._customers[index]]
        customer = self._customers[index]
        return CustomerForCrm(customer.id, customer.name, customer.phone)


def search_customers_for_crm(company_id: UUID, search: str | None = None,
                             customer_ids: Collection[UUID] | None = None) -> CrmCustomerList:
    """Clientes activos de la empresa por nombre e id (búsqueda por nombre o teléfono; `customer_ids` restringe)."""
    return CrmCustomerList(DjangoCustomerRepository(company_id).list(
        search=(search or '').strip() or None, active=True, ids=customer_ids))


# --- Escritura para la importación de ventas (TASK-cargar-ventas-desde-archivo) -----------------------------

@dataclass(frozen=True)
class CustomerForImport:
    id: UUID
    name: str
    active: bool


def list_customers_for_import(company_id: UUID) -> list[CustomerForImport]:
    """Todos los clientes de la empresa (activos e inactivos) para casar por nombre; solo lectura."""
    rows = (CustomerModel.objects.filter(company_id=company_id).order_by('name', 'id')
            .values_list('id', 'name', 'active'))
    return [CustomerForImport(id=i, name=n, active=a) for i, n, a in rows]


def create_customer_for_import(company_id: UUID, name: str) -> CustomerForImport:
    """Crea un cliente solo con nombre (sin teléfono, así no hay aviso de duplicado) con el caso de uso de Clientes."""
    from django.conf import settings

    from modules.customers.application.commands import CreateCustomer

    from modules.customers.domain.exceptions import CustomerValidationError
    from shared.import_errors import ImportRejected, first_error

    try:
        customer = CreateCustomer(DjangoCustomerRepository(company_id), settings.DEFAULT_PHONE_COUNTRY_CODE).execute(
            name=name)
    except CustomerValidationError as exc:
        field, message = first_error(exc.errors)
        raise ImportRejected('customer_rejected', message, field) from exc
    return CustomerForImport(id=customer.id, name=customer.name, active=customer.active)
