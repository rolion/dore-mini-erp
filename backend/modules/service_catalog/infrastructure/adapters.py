"""Bridge from Services to the public Personal facade."""
from uuid import UUID

from modules.personnel import services as personnel_services


class PersonnelSpecialties:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def accepts(self, specialty_id: UUID) -> bool:
        return personnel_services.specialty_is_available(self.company_id, specialty_id)


def specialty_names(company_id: UUID, ids: set[UUID]) -> dict[UUID, str]:
    return personnel_services.specialty_names(company_id, ids)
