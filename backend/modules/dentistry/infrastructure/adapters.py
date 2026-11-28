from contextlib import contextmanager

from modules.agenda import services as agenda_services
from modules.customers.services import get_customers_administrative, search_customer_ids
from modules.dentistry.domain.encounter import EncounterStateError
from modules.dentistry.domain.patient import PatientArchived, PatientNotFound
from modules.dentistry.domain.proforma import DentalProformaValidationError
from modules.personnel.services import professional_exists, professional_names
from modules.service_catalog.services import ServiceSnapshot, get_service_for_new_use
from shared import module_gate

from .encounter_models import EncounterModel
from .models import PatientModel


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
        self.company_id, self.services = company_id, agenda_services

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

    def in_range(self, **filters):
        return self.services.appointments_in_range(self.company_id, **filters)

    def attend(self, actor_id, actor_name, appointment_id):
        with self._translated():
            self.services.attend_by_clinic(self.company_id, self.services.Actor(actor_id, actor_name), appointment_id)

    def cancel(self, actor_id, actor_name, appointment_id, reason):
        with self._translated():
            self.services.cancel_by_clinic(
                self.company_id, self.services.Actor(actor_id, actor_name), appointment_id, reason)

    @contextmanager
    def _translated(self):
        """Los errores de Agenda salen como errores de estado de la atención (409)."""
        try:
            yield
        except (self.services.AppointmentConflict, self.services.AppointmentRuleError) as exc:
            raise EncounterStateError(exc.message, getattr(exc, 'code', 'invalid_transition')) from exc


CLINICAL_FLOW = 'clinical_flow_required'
ENCOUNTER_STARTED = 'encounter_started'


def appointment_guard(company_id, appointment, action):
    """Guarda que Odontología registra en Agenda: las citas con atención o de pacientes odontológicos se gestionan
    por el flujo clínico (PB-ODO-007)."""
    veto = agenda_services.Veto
    if EncounterModel.objects.filter(company_id=company_id, appointment_id=appointment.id).exists():
        if action == 'attend':
            return veto(CLINICAL_FLOW, 'Esta cita tiene una atención odontológica: finalízala desde Odontología.')
        return veto(ENCOUNTER_STARTED,
                    'La cita tiene una atención odontológica iniciada; gestiónala desde Odontología.')
    if action == 'attend' and module_gate.is_enabled(company_id, 'dentistry') and PatientModel.objects.filter(
            company_id=company_id, customer_id=appointment.customer_id).exists():
        return veto(CLINICAL_FLOW, 'La cita de un paciente odontológico se atiende desde Odontología.')
    return None


def register_agenda_guard() -> None:
    agenda_services.register_guard(appointment_guard)
