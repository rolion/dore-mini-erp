from modules.customers.services import get_customers_administrative, search_customer_ids
from modules.dentistry.domain.patient import PatientArchived, PatientNotFound
from modules.dentistry.domain.proforma import DentalProformaValidationError
from modules.personnel.services import professional_exists, professional_names
from modules.service_catalog.services import ServiceSnapshot, get_service_for_new_use


class CustomersAdapter:
    def __init__(self, company_id):
        self.company_id = company_id

    def get_many(self, ids):
        return get_customers_administrative(self.company_id, ids)

    def search_ids(self, search):
        return search_customer_ids(self.company_id, search)


class ProfessionalLookup:
    """Profesionales de Personal (fachada pública) para identificar a quien atiende una evaluación."""

    def __init__(self, company_id):
        self.company_id = company_id

    def exists(self, professional_id) -> bool:
        return professional_exists(self.company_id, professional_id)

    def names(self, ids) -> dict:
        return professional_names(self.company_id, set(ids))


class ServiceLookup:
    """Servicios del catálogo para nuevas líneas de proforma (fachada pública de Servicios)."""

    def __init__(self, company_id):
        self.company_id = company_id

    def for_new_use(self, service_id) -> ServiceSnapshot | None:
        return get_service_for_new_use(self.company_id, service_id)


class PatientGate:
    """Comprueba que el paciente exista, esté activo y su cliente también; devuelve su nombre vigente."""

    def __init__(self, patients, customers):
        self.patients, self.customers = patients, customers

    def require_active(self, customer_id) -> str:
        row = self.patients.get(customer_id)  # PatientNotFound si no existe o es de otra empresa
        if not row.active:
            raise PatientArchived('Reactiva el perfil odontológico antes de trabajar con sus proformas.')
        customer = self.customers.get_many([customer_id]).get(customer_id)
        if customer is None:
            raise PatientNotFound('Paciente no encontrado.')
        if not customer.active:
            raise DentalProformaValidationError({'customer_id': ['El cliente está inactivo.']})
        return customer.name


class AgendaAdapter:
    """Citas de Agenda por su fachada pública; los comandos clínicos no pasan por las guardas de Agenda."""

    def __init__(self, company_id):
        from modules.agenda import services
        self.company_id, self.services = company_id, services

    def get(self, appointment_id):
        return self.services.get_appointment(self.company_id, appointment_id)

    def get_many(self, ids):
        return self.services.get_appointments(self.company_id, ids)

    def lock(self, appointment_id):
        """None si la cita no existe en la empresa."""
        try:
            return self.services.lock_appointment(self.company_id, appointment_id)
        except self.services.AppointmentNotFound:
            return None

    def search(self, **filters):
        return self.services.search_appointments(self.company_id, **filters)

    def attend(self, actor_id, actor_name, appointment_id):
        self.services.attend_by_clinic(self.company_id, self.services.Actor(actor_id, actor_name), appointment_id)

    def cancel(self, actor_id, actor_name, appointment_id, reason):
        self.services.cancel_by_clinic(
            self.company_id, self.services.Actor(actor_id, actor_name), appointment_id, reason)
