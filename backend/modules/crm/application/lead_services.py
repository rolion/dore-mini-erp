"""Casos de uso de prospectos y conversión en cliente (AC-01, AC-05). El llamador abre la transacción."""
from dataclasses import dataclass
from uuid import UUID

from modules.crm.domain.errors import CrmConflict, CrmNotFound, CrmValidationError
from modules.crm.domain.lead import Lead

from .ports import CustomerContact, CustomerGateway, CustomerGatewayError

UNSET = object()


@dataclass(frozen=True)
class Conversion:
    lead: Lead
    customer: CustomerContact
    created: bool


class LeadService:
    def __init__(self, leads, opportunities, customers: CustomerGateway):
        self.leads, self.opportunities, self.customers = leads, opportunities, customers

    def _get(self, lead_id: UUID, *, for_update: bool = False) -> Lead:
        lead = self.leads.get(lead_id, for_update=for_update)
        if lead is None:
            raise CrmNotFound('Prospecto no encontrado.')
        return lead

    def get(self, lead_id: UUID) -> Lead:
        return self._get(lead_id)

    def list(self, *, search: str | None = None, converted: bool | None = None):
        return self.leads.list(search=search, converted=converted)

    def create(self, name: object, phone: object = '', email: object = '') -> Lead:
        phone_text = phone.strip() if isinstance(phone, str) else ''
        lead = Lead.create(name, phone, email, normalized_phone=self.customers.normalize_phone(phone_text))
        return self.leads.save(lead)

    def edit(self, lead_id: UUID, *, name: object = UNSET, phone: object = UNSET, email: object = UNSET) -> Lead:
        lead = self._get(lead_id, for_update=True)
        new_name = lead.name if name is UNSET else name
        new_phone = lead.phone if phone is UNSET else phone
        new_email = lead.email if email is UNSET else email
        phone_text = new_phone.strip() if isinstance(new_phone, str) else ''
        lead.edit(new_name, new_phone, new_email, self.customers.normalize_phone(phone_text))
        return self.leads.save(lead)

    def convert(self, lead_id: UUID, customer_id: UUID | None = None) -> Conversion:
        """Conversión idempotente (INV-04, INV-05): bloquea el prospecto; repetir devuelve el mismo cliente."""
        lead = self._get(lead_id, for_update=True)
        if lead.is_converted:
            customer = self.customers.get(lead.converted_customer_id)
            if customer is None:  # el cliente ya no existe: se informa la referencia guardada
                customer = CustomerContact(lead.converted_customer_id, '', '', False)
            return Conversion(lead=lead, customer=customer, created=False)
        customer, created = self._resolve_customer(lead, customer_id)
        lead.convert_to(customer.id)
        lead = self.leads.save(lead)
        for opportunity in self.opportunities.open_for_lead(lead.id):
            if opportunity.attach_customer(customer.id):
                self.opportunities.save(opportunity)
        return Conversion(lead=lead, customer=customer, created=created)

    def _resolve_customer(self, lead: Lead, customer_id: UUID | None) -> tuple[CustomerContact, bool]:
        if customer_id is not None:
            customer = self.customers.get(customer_id)
            if customer is None:
                raise CrmNotFound('Cliente no encontrado.')
            if not customer.active:
                raise CrmValidationError({'customer_id': ['El cliente está inactivo.']})
            return customer, False
        matches = self.customers.find_active_by_phone(lead.normalized_phone) if lead.normalized_phone else []
        if len(matches) == 1:
            return matches[0], False
        if matches:
            raise CrmConflict('multiple_customer_matches', 'Hay varios clientes con este teléfono: elige uno.',
                              candidates=[{'id': str(c.id), 'name': c.name, 'phone': c.phone} for c in matches])
        try:
            return self.customers.create(lead.name, lead.phone, lead.email), True
        except CustomerGatewayError as exc:
            raise CrmValidationError(exc.errors) from exc
