"""Bandeja de WhatsApp: asignar, vincular a contacto y oportunidad, responder (PB-CRM-012). Las reglas de coherencia
(INV-02…07) viven aquí; `messaging` solo guarda los identificadores (ADR)."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from modules.crm.domain.errors import CrmConflict, CrmNotFound, CrmValidationError
from modules.crm.domain.opportunity import Opportunity

from .ports import (
    ConversationInbox,
    CustomerDirectory,
    CustomerGateway,
    InboxConversation,
    InboxMessage,
    UserDirectory,
)

SCOPES = ('mine', 'unassigned', 'all')
SEARCH_LIMIT = 200  # contactos que se consideran al buscar por nombre


@dataclass(frozen=True)
class ContactRef:
    type: str  # 'customer' | 'lead'
    id: UUID
    name: str


@dataclass(frozen=True)
class OpportunityRef:
    id: UUID
    title: str


@dataclass(frozen=True)
class InboxItem:
    conversation: InboxConversation
    contact: ContactRef | None
    owner_name: str
    opportunity: OpportunityRef | None
    connection_active: bool | None = None


class InboxService:
    def __init__(self, *, inbox: ConversationInbox, customers: CustomerGateway, customer_directory: CustomerDirectory,
                 leads, opportunities, users: UserDirectory, opportunity_service):
        self.inbox, self.customers, self.customer_directory = inbox, customers, customer_directory
        self.leads, self.opportunities, self.users = leads, opportunities, users
        self.opportunity_service = opportunity_service

    # --- lectura -------------------------------------------------------------------------------------------

    def _describe(self, conversations: Sequence[InboxConversation]) -> list[InboxItem]:
        """Contacto, responsable y oportunidad de una página, resueltos por lote (sin N+1)."""
        leads = self.leads.get_many({c.lead_id for c in conversations if c.lead_id})
        customer_ids = {c.customer_id for c in conversations if c.customer_id}
        customer_ids |= {lead.converted_customer_id for lead in leads.values() if lead.converted_customer_id}
        customers = self.customers.get_many(customer_ids)
        opportunities = self.opportunities.get_many({c.opportunity_id for c in conversations if c.opportunity_id})
        owners = self.users.names({c.owner_id for c in conversations if c.owner_id})
        items = []
        for c in conversations:
            contact = None
            if c.customer_id:
                found = customers.get(c.customer_id)
                contact = ContactRef('customer', c.customer_id, found.name if found else '')
            elif c.lead_id:
                lead = leads.get(c.lead_id)
                converted = customers.get(lead.converted_customer_id) if lead and lead.converted_customer_id else None
                if converted is not None:  # el prospecto ya es cliente: se muestra el cliente (EDGE)
                    contact = ContactRef('customer', converted.id, converted.name)
                else:
                    contact = ContactRef('lead', c.lead_id, lead.name if lead else '')
            opportunity = opportunities.get(c.opportunity_id) if c.opportunity_id else None
            items.append(InboxItem(c, contact, owners.get(c.owner_id, '') if c.owner_id else '',
                                   OpportunityRef(opportunity.id, opportunity.title) if opportunity else None))
        return items

    def list(self, *, actor_id: int, scope: str = 'all', search: str | None = None,
             opportunity_id: UUID | None = None, offset: int = 0, limit: int = 25) -> tuple[int, list[InboxItem]]:
        if scope not in SCOPES:
            raise CrmValidationError({'scope': ['Usa mine, unassigned o all.']})
        customer_ids: list[UUID] = []
        lead_ids: list[UUID] = []
        search = (search or '').strip() or None
        if search:
            customer_ids = [c.id for c in self.customer_directory.search_active(search, None)[:SEARCH_LIMIT]]
            lead_ids = [lead.id for lead in self.leads.list(search=search)[:SEARCH_LIMIT]]
        total, conversations = self.inbox.page(
            owner_id=actor_id if scope == 'mine' else None, unassigned=scope == 'unassigned',
            opportunity_id=opportunity_id, search=search, customer_ids=customer_ids, lead_ids=lead_ids,
            offset=offset, limit=limit)
        return total, self._describe(conversations)

    def get(self, conversation_id: UUID) -> InboxItem:
        item = self._describe([self.inbox.get(conversation_id)])[0]
        return InboxItem(item.conversation, item.contact, item.owner_name, item.opportunity,
                         self.inbox.connection_active())

    def messages(self, conversation_id: UUID, after: datetime | None = None) -> list[InboxMessage]:
        return self.inbox.messages(conversation_id, after)

    def linkable_opportunities(self, conversation_id: UUID) -> list[Opportunity]:
        """Oportunidades abiertas del contacto de la conversación (vacío si aún no tiene contacto)."""
        conversation = self.inbox.get(conversation_id)
        customer_id, lead_id = self._contact_ids(conversation)
        if customer_id is None and lead_id is None:
            return []
        return self.opportunities.open_for_contact(customer_id, lead_id)

    # --- responder -----------------------------------------------------------------------------------------

    def send_text(self, conversation_id: UUID, body: str) -> InboxMessage:
        return self.inbox.send_text(conversation_id, body)

    def send_template(self, conversation_id: UUID, template_id: UUID, components: list | None = None
                      ) -> InboxMessage:
        return self.inbox.send_template(conversation_id, template_id, components)

    def retry(self, conversation_id: UUID, message_id: UUID) -> InboxMessage:
        return self.inbox.retry(conversation_id, message_id)

    # --- asignar y vincular --------------------------------------------------------------------------------

    def assign(self, conversation_id: UUID, owner_id: int | None) -> InboxItem:
        if owner_id is not None and not self.users.exists(owner_id):  # INV-02
            raise CrmValidationError({'owner_id': ['Elige un usuario de tu empresa.']})
        self.inbox.get(conversation_id)
        self.inbox.assign(conversation_id, owner_id)
        return self.get(conversation_id)

    @staticmethod
    def _contact_ids(conversation: InboxConversation) -> tuple[UUID | None, UUID | None]:
        return conversation.customer_id, conversation.lead_id

    def _matches(self, opportunity: Opportunity, customer_id: UUID | None, lead_id: UUID | None) -> bool:
        """INV-05: misma persona (cliente, prospecto o el prospecto ya convertido a ese cliente)."""
        if customer_id is not None:
            if opportunity.customer_id == customer_id:
                return True
            lead = self.leads.get(opportunity.lead_id) if opportunity.lead_id else None
            return lead is not None and lead.converted_customer_id == customer_id
        return lead_id is not None and opportunity.lead_id == lead_id

    def set_contact(self, conversation_id: UUID, *, customer_id: UUID | None = None,
                    lead_id: UUID | None = None) -> InboxItem:
        if customer_id is not None and lead_id is not None:  # INV-03
            raise CrmValidationError({'customer_id': ['Vincula un cliente o un prospecto, no ambos.']})
        conversation = self.inbox.get(conversation_id)
        if customer_id is not None:  # INV-04
            customer = self.customers.get(customer_id)
            if customer is None:
                raise CrmNotFound('Cliente no encontrado.')
            if not customer.active:
                raise CrmConflict('customer_inactive', 'El cliente está inactivo.')
        if lead_id is not None and self.leads.get(lead_id) is None:
            raise CrmNotFound('Prospecto no encontrado.')
        opportunity_id = conversation.opportunity_id
        if opportunity_id is not None:  # INV-06
            opportunity = self.opportunities.get(opportunity_id)
            if opportunity is None or not self._matches(opportunity, customer_id, lead_id):
                opportunity_id = None
        self.inbox.link(conversation_id, customer_id, lead_id, opportunity_id)
        return self.get(conversation_id)

    def set_opportunity(self, conversation_id: UUID, opportunity_id: UUID | None) -> InboxItem:
        conversation = self.inbox.get(conversation_id)
        customer_id, lead_id = self._contact_ids(conversation)
        if opportunity_id is None:
            self.inbox.link(conversation_id, customer_id, lead_id, None)
            return self.get(conversation_id)
        opportunity = self.opportunities.get(opportunity_id)
        if opportunity is None:
            raise CrmNotFound('Oportunidad no encontrada.')
        if not opportunity.is_open:
            raise CrmConflict('opportunity_closed', 'La oportunidad está cerrada: no se puede vincular.')
        if customer_id is None and lead_id is None:  # hereda el contacto de la oportunidad (INV-05)
            customer_id = opportunity.customer_id
            lead_id = None if customer_id else opportunity.lead_id
        elif not self._matches(opportunity, customer_id, lead_id):
            raise CrmConflict('contact_mismatch', 'La oportunidad es de otro contacto.')
        self.inbox.link(conversation_id, customer_id, lead_id, opportunity.id)
        return self.get(conversation_id)

    def create_opportunity(self, conversation_id: UUID, *, actor_id: int, **values) -> InboxItem:
        """Crea la oportunidad para el contacto de la conversación y la vincula (una sola operación en la vista)."""
        conversation = self.inbox.get(conversation_id)
        customer_id, lead_id = self._contact_ids(conversation)
        if customer_id is None and lead_id is None:
            raise CrmValidationError({'customer_id': ['Vincula primero un contacto a la conversación.']})
        opportunity = self.opportunity_service.create(actor_id=actor_id, customer_id=customer_id, lead_id=lead_id,
                                                      **values)
        self.inbox.link(conversation_id, customer_id, lead_id, opportunity.id)
        return self.get(conversation_id)

    # --- autovínculo ---------------------------------------------------------------------------------------

    def auto_link(self, conversation_id: UUID) -> bool:
        """INV-07: solo sin contacto y con coincidencia única (cliente activo o, si no hay, prospecto sin convertir)."""
        conversation = self.inbox.get(conversation_id)
        if conversation.customer_id is not None or conversation.lead_id is not None:
            return False
        phone = self.customers.normalize_phone('+' + conversation.phone)
        customers = self.customers.find_active_by_phone(phone)
        if len(customers) == 1:
            self.inbox.link(conversation_id, customers[0].id, None, conversation.opportunity_id)
            return True
        if customers:
            return False
        leads = self.leads.find_unconverted_by_phone(phone)
        if len(leads) == 1:
            self.inbox.link(conversation_id, None, leads[0].id, conversation.opportunity_id)
            return True
        return False
