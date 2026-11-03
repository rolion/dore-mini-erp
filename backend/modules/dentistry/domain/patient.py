from dataclasses import dataclass, field
from uuid import UUID

CLINICAL_FIELDS = ('medical_history', 'dental_history', 'allergies', 'medication', 'clinical_notes')


class PatientInvalid(Exception):
    def __init__(self, errors):
        self.errors = errors


class PatientNotFound(Exception):
    pass


class DuplicatePatient(Exception):
    pass


class PatientArchived(Exception):
    pass


@dataclass
class Patient:
    customer_id: UUID
    active: bool = True
    clinical: dict[str, str] = field(default_factory=lambda: dict.fromkeys(CLINICAL_FIELDS, ''))

    def edit(self, changes: dict[str, str]) -> None:
        if not self.active:
            raise PatientArchived('Reactiva el perfil antes de editarlo.')
        errors, cleaned = {}, {}
        for key in CLINICAL_FIELDS:
            if key not in changes:
                continue
            value = changes[key]
            if not isinstance(value, str) or len(value.strip()) > 4000:
                errors[key] = ['Debe ser texto de hasta 4000 caracteres.']
            else:
                cleaned[key] = value.strip()
        if errors:
            raise PatientInvalid(errors)
        self.clinical.update(cleaned)

    def archive(self):
        self.active = False

    def activate(self):
        self.active = True

    def snapshot(self):
        return {'active': self.active, **self.clinical}
