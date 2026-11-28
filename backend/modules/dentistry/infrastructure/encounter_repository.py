from modules.dentistry.domain.encounter import Encounter, EncounterNotFound
from .encounter_models import EncounterModel


def to_domain(row: EncounterModel) -> Encounter:
    return Encounter(row.appointment_id, row.customer_id, row.professional_id, status=row.status,
                     started_at=row.started_at, finished_at=row.finished_at, cancelled_at=row.cancelled_at,
                     cancellation_reason=row.cancellation_reason, observations=row.observations, id=row.id)


class DjangoEncounterRepository:
    def __init__(self, company_id):
        self.company_id = company_id

    def rows(self):
        return EncounterModel.objects.filter(company_id=self.company_id)

    def get(self, encounter_id, *, locked=False) -> EncounterModel:
        rows = self.rows().select_for_update() if locked else self.rows()
        row = rows.filter(id=encounter_id).first()
        if row is None:
            raise EncounterNotFound('Atención no encontrada.')
        return row

    def for_appointment(self, appointment_id, *, locked=False) -> EncounterModel | None:
        rows = self.rows().select_for_update() if locked else self.rows()
        return rows.filter(appointment_id=appointment_id).first()

    def for_customer(self, customer_id):
        return self.rows().filter(customer_id=customer_id)

    @staticmethod
    def entity(row: EncounterModel) -> Encounter:
        return to_domain(row)

    def create(self, encounter: Encounter, author_id, author_name) -> EncounterModel:
        return EncounterModel.objects.create(
            id=encounter.id, company_id=self.company_id, appointment_id=encounter.appointment_id,
            customer_id=encounter.customer_id, professional_id=encounter.professional_id, status=encounter.status,
            started_at=encounter.started_at, started_by=author_id, started_by_name=author_name)

    @staticmethod
    def save(row: EncounterModel, encounter: Encounter, author_id=None, author_name='') -> None:
        row.status, row.observations = encounter.status, encounter.observations
        fields = ['status', 'observations', 'updated_at']
        if encounter.finished_at and not row.finished_at:
            row.finished_at, row.finished_by, row.finished_by_name = encounter.finished_at, author_id, author_name
            fields += ['finished_at', 'finished_by', 'finished_by_name']
        if encounter.cancelled_at and not row.cancelled_at:
            row.cancelled_at, row.cancelled_by, row.cancelled_by_name = encounter.cancelled_at, author_id, author_name
            row.cancellation_reason = encounter.cancellation_reason
            fields += ['cancelled_at', 'cancelled_by', 'cancelled_by_name', 'cancellation_reason']
        row.save(update_fields=fields)
