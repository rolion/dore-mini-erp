from modules.customers.services import get_customers_administrative, search_customer_ids
from modules.dentistry.domain.patient import PatientArchived, PatientNotFound
from modules.dentistry.domain.proforma import DentalProformaValidationError
from modules.service_catalog.services import ServiceSnapshot, get_service_for_new_use


class CustomersAdapter:
    def __init__(self, company_id):
        self.company_id = company_id

    def get_many(self, ids):
        return get_customers_administrative(self.company_id, ids)

    def search_ids(self, search):
        return search_customer_ids(self.company_id, search)


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
