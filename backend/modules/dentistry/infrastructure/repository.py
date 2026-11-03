from modules.dentistry.domain.patient import CLINICAL_FIELDS, Patient, PatientNotFound
from .models import PatientModel, PatientHistoryModel


def to_patient(row):
    return Patient(row.customer_id, row.active, {key: getattr(row, key) for key in CLINICAL_FIELDS})


class DjangoPatientRepository:
    def __init__(self, company_id):
        self.company_id = company_id

    def rows(self):
        return PatientModel.objects.filter(company_id=self.company_id)

    @staticmethod
    def entity(row):
        return to_patient(row)

    def get(self, customer_id, *, locked=False):
        rows = self.rows().select_for_update() if locked else self.rows()
        row = rows.filter(customer_id=customer_id).first()
        if row is None:
            raise PatientNotFound('Paciente no encontrado.')
        return row

    def create(self, patient, author_id):
        return PatientModel.objects.create(company_id=self.company_id, customer_id=patient.customer_id,
                                           created_by=author_id, updated_by=author_id, **patient.snapshot())

    def save(self, row, patient, author_id):
        for key, value in patient.snapshot().items():
            setattr(row, key, value)
        row.updated_by = author_id
        row.save(update_fields=['active', *CLINICAL_FIELDS, 'updated_by', 'updated_at'])

    def audit(self, row, author_id, author_name, action, before, after):
        PatientHistoryModel.objects.create(company_id=self.company_id, patient=row, author_id=author_id,
                                           author_name=author_name, action=action, before=before, after=after)

    def history(self, customer_id):
        row = self.get(customer_id)
        return PatientHistoryModel.objects.filter(company_id=self.company_id, patient=row)
