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


# --- Prospectos de CRM (TASK-crm-prospectos-oportunidades) -------------------------------------------------

@dataclass(frozen=True)
class CustomerContactForCrm:
    id: UUID
    name: str
    phone: str
    active: bool


class CustomerRejected(Exception):
    """Clientes rechazó los datos al crear el cliente: `errors` es `{campo: [mensajes]}`."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


def _contact(customer) -> CustomerContactForCrm:
    return CustomerContactForCrm(id=customer.id, name=customer.name, phone=customer.phone, active=customer.active)


def normalize_phone_for_crm(raw: str) -> str:
    """El teléfono tal como lo guarda Clientes (misma normalización y país por defecto); vacío si no hay."""
    from django.conf import settings

    from modules.customers.domain.customer import normalize_phone

    return normalize_phone(raw, settings.DEFAULT_PHONE_COUNTRY_CODE) if (raw or '').strip() else ''


def find_active_customers_by_phone(company_id: UUID, normalized_phone: str,
                                   limit: int = 10) -> list[CustomerContactForCrm]:
    """Clientes **activos** de la empresa con ese teléfono ya normalizado (por nombre); vacío sin teléfono."""
    if not normalized_phone:
        return []
    return [_contact(c) for c in DjangoCustomerRepository(company_id).find_by_phone(normalized_phone, limit=limit * 2)
            if c.active][:limit]


def get_customer_for_crm(company_id: UUID, customer_id: UUID) -> CustomerContactForCrm | None:
    """El cliente de la empresa con su estado (activo o no), o `None` si no existe o es de otra empresa."""
    customer = DjangoCustomerRepository(company_id).get(customer_id)
    return _contact(customer) if customer else None


def get_customers_for_crm(company_id: UUID, customer_ids: Iterable[UUID]) -> dict[UUID, CustomerContactForCrm]:
    """Contactos de varios clientes de la empresa en una sola consulta; los ids inexistentes no aparecen."""
    ids = set(customer_ids)
    if not ids:
        return {}
    rows = CustomerModel.objects.filter(company_id=company_id, pk__in=ids).values_list('id', 'name', 'phone', 'active')
    return {i: CustomerContactForCrm(id=i, name=n, phone=p, active=a) for i, n, p, a in rows}


def create_customer_for_crm(company_id: UUID, name: str, phone: str = '', email: str = '') -> CustomerContactForCrm:
    """Crea el cliente con el caso de uso de Clientes. CRM ya resolvió los duplicados por teléfono, por eso se
    confirma el aviso; lanza `CustomerRejected` si Clientes rechaza los datos."""
    from django.conf import settings

    from modules.customers.application.commands import CreateCustomer
    from modules.customers.domain.exceptions import CustomerValidationError

    try:
        customer = CreateCustomer(DjangoCustomerRepository(company_id), settings.DEFAULT_PHONE_COUNTRY_CODE).execute(
            name=name, phone=phone, email=email, confirm_duplicate=True)
    except CustomerValidationError as exc:
        raise CustomerRejected(exc.errors) from exc
    return _contact(customer)
