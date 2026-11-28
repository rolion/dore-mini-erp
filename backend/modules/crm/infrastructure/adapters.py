"""Único lugar de CRM que conoce a Clientes, Ventas e Inventario, y solo por sus `services.py`."""
from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from django.utils import timezone

from modules.crm.domain.errors import CrmConflict, CrmNotFound, CrmValidationError
from modules.crm.application.ports import (
    InboxConversation,
    InboxMessage,
    CommercialSummary,
    CustomerContact,
    CustomerGatewayError,
    CustomerRef,
    OrderRef,
)
from modules.customers import services as customer_services
from modules.inventory import services as inventory_services
from modules.messaging import services as messaging_services
from modules.sales import services as sales_services
from shared import module_gate
from shared.identity import CompanyUserDirectory


class _CustomerRows:
    def __init__(self, rows):
        self._rows = rows

    def count(self) -> int:
        return self._rows.count()

    def __getitem__(self, index):
        found = self._rows[index]
        if isinstance(index, slice):
            return [CustomerRef(c.id, c.name, c.phone) for c in found]
        return CustomerRef(found.id, found.name, found.phone)


class CustomerDirectoryAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def search_active(self, search: str | None, customer_ids: Collection[UUID] | None):
        return _CustomerRows(customer_services.search_customers_for_crm(self.company_id, search, customer_ids))


class SalesReaderAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def summaries(self, customer_ids: Collection[UUID]) -> dict[UUID, CommercialSummary]:
        found = sales_services.get_customer_commercial_summaries(self.company_id, customer_ids)
        return {
            customer_id: CommercialSummary(s.order_count, s.last_purchase_date, s.outstanding_amount)
            for customer_id, s in found.items()
        }

    def customer_ids_in_warehouse(self, warehouse_id: UUID) -> list[UUID]:
        return sales_services.list_customer_ids_with_orders_in_warehouse(self.company_id, warehouse_id)


class WarehouseDirectoryAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def exists(self, warehouse_id: UUID) -> bool:
        # Sucursal = almacén activo de la empresa (los inactivos no se ofrecen como filtro).
        return any(w.id == warehouse_id for w in inventory_services.list_active_warehouses(self.company_id))


class ModuleAvailabilityAdapter:
    """Ventas e Inventario son fuentes opcionales: se consultan una vez por petición."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self._enabled: frozenset[str] | None = None

    def _keys(self) -> frozenset[str]:
        if self._enabled is None:
            self._enabled = module_gate.enabled_keys(self.company_id)
        return self._enabled

    def sales_enabled(self) -> bool:
        return 'sales' in self._keys()

    def inventory_enabled(self) -> bool:
        return 'inventory' in self._keys()


def system_clock() -> datetime:
    return timezone.now()


def _contact(found) -> CustomerContact:
    return CustomerContact(found.id, found.name, found.phone, found.active)


class CustomerGatewayAdapter:
    """Prospectos ↔ Clientes: normalizar teléfono, buscar coincidencias y crear el cliente al convertir."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def normalize_phone(self, raw: str) -> str:
        return customer_services.normalize_phone_for_crm(raw)

    def find_active_by_phone(self, normalized_phone: str) -> list[CustomerContact]:
        found = customer_services.find_active_customers_by_phone(self.company_id, normalized_phone)
        return [_contact(c) for c in found]

    def get(self, customer_id: UUID) -> CustomerContact | None:
        found = customer_services.get_customer_for_crm(self.company_id, customer_id)
        return _contact(found) if found else None

    def get_many(self, customer_ids: Collection[UUID]) -> dict[UUID, CustomerContact]:
        found = customer_services.get_customers_for_crm(self.company_id, customer_ids)
        return {i: _contact(c) for i, c in found.items()}

    def create(self, name: str, phone: str, email: str) -> CustomerContact:
        try:
            return _contact(customer_services.create_customer_for_crm(self.company_id, name, phone, email))
        except customer_services.CustomerRejected as exc:
            raise CustomerGatewayError(exc.errors) from exc


def _order(found) -> OrderRef:
    return OrderRef(found.id, found.customer_id, found.order_date, found.total, found.status, found.cancelled)


class OrderGatewayAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get(self, order_id: UUID) -> OrderRef | None:
        found = sales_services.get_order_for_crm(self.company_id, order_id)
        return _order(found) if found else None

    def list_for_customer(self, customer_id: UUID) -> list[OrderRef]:
        return [_order(o) for o in sales_services.list_orders_for_customer_for_crm(self.company_id, customer_id)]


class UserDirectoryAdapter:
    """Responsables = usuarios de la empresa, por el directorio neutral (CRM no conoce `accounts`)."""

    def __init__(self, company_id: UUID):
        self._directory = CompanyUserDirectory(company_id)

    def exists(self, user_id: int) -> bool:
        return self._directory.exists(user_id)

    def names(self, user_ids: Collection[int]) -> dict[int, str]:
        wanted = set(user_ids)
        if not wanted:
            return {}
        return {row['id']: row['name'] for row in self._directory.list() if row['id'] in wanted}

    def search(self, search: str = '') -> list[dict]:
        """Usuarios de la empresa (`{id, name}`) cuyo nombre o usuario contiene el texto."""
        return list(self._directory.list(search=search))


def subscribe_inbound(handler) -> None:
    """Avisa `handler(company_id, conversation_id)` por cada mensaje entrante nuevo (alta al arrancar la app)."""
    messaging_services.subscribe_inbound(handler)


def _inbox_message(m) -> InboxMessage:
    return InboxMessage(m.id, m.direction, m.type, m.content, m.status, m.failure_reason, m.created_at, m.sent_at)


def _inbox_conversation(summary) -> InboxConversation:
    c, last = summary.conversation, summary.last_message
    return InboxConversation(c.id, c.phone, c.owner_id, c.customer_id, c.lead_id, c.opportunity_id,
                             _inbox_message(last) if last else None, summary.window_open, summary.window_expires_at)


_MESSAGES = {
    'window_closed': 'La ventana de 24 h está cerrada: envía una plantilla aprobada.',
    'template_not_approved': 'La plantilla no está aprobada.',
    'connection_not_active': 'La conexión de WhatsApp no está activa.',
    'not_retryable': 'Solo se puede reenviar un mensaje que falló.',
}


def _translated(call):
    """Los errores de `messaging` se presentan con los de CRM: la API de la bandeja solo conoce estos."""
    try:
        return call()
    except messaging_services.MessagingNotFound as exc:
        raise CrmNotFound('No encontrado.') from exc
    except messaging_services.MessagingValidationError as exc:
        raise CrmValidationError(exc.errors) from exc
    except (messaging_services.WindowClosed, messaging_services.TemplateNotApproved,
            messaging_services.ConnectionNotActive, messaging_services.NotRetryable) as exc:
        raise CrmConflict(exc.code, _MESSAGES[exc.code]) from exc


class ConversationInboxAdapter:
    """Único lugar de la bandeja que conoce a `messaging`, y solo por su `services.py`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def page(self, *, owner_id, unassigned, opportunity_id, search, customer_ids, lead_ids, offset, limit):
        total, rows = messaging_services.list_conversations(
            self.company_id, owner_id=owner_id, unassigned=unassigned, opportunity_id=opportunity_id,
            search=search, customer_ids=customer_ids, lead_ids=lead_ids, offset=offset, limit=limit)
        return total, [_inbox_conversation(r) for r in rows]

    def get(self, conversation_id: UUID) -> InboxConversation:
        return _translated(lambda: _inbox_conversation(
            messaging_services.get_conversation(self.company_id, conversation_id)))

    def messages(self, conversation_id: UUID, after: datetime | None):
        return _translated(lambda: [_inbox_message(m) for m in messaging_services.list_messages(
            self.company_id, conversation_id, after)])

    def connection_active(self) -> bool:
        return messaging_services.connection_active(self.company_id)

    def send_text(self, conversation_id: UUID, body: str) -> InboxMessage:
        return _translated(lambda: _inbox_message(messaging_services.send_text(self.company_id, conversation_id, body)))

    def send_template(self, conversation_id: UUID, template_id: UUID, components) -> InboxMessage:
        return _translated(lambda: _inbox_message(messaging_services.send_template(
            self.company_id, conversation_id, template_id, components)))

    def retry(self, conversation_id: UUID, message_id: UUID) -> InboxMessage:
        return _translated(lambda: _inbox_message(messaging_services.retry_message(
            self.company_id, conversation_id, message_id)))

    def assign(self, conversation_id: UUID, owner_id: int | None) -> None:
        _translated(lambda: messaging_services.assign(self.company_id, conversation_id, owner_id))

    def link(self, conversation_id, customer_id, lead_id, opportunity_id) -> None:
        _translated(lambda: messaging_services.link_contact(
            self.company_id, conversation_id, customer_id, lead_id, opportunity_id))
