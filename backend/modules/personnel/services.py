"""Public specialty lookups for other business modules."""
from uuid import UUID

from modules.personnel.infrastructure.django.models import ProfessionalModel, SpecialtyModel
from shared import module_gate


def specialty_is_available(company_id: UUID, specialty_id: UUID) -> bool:
    if not module_gate.is_enabled(company_id, 'personnel'):
        return False
    return SpecialtyModel.objects.filter(company_id=company_id, id=specialty_id, active=True).exists()


def specialty_names(company_id: UUID, ids: set[UUID]) -> dict[UUID, str]:
    if not ids:
        return {}
    return dict(SpecialtyModel.objects.filter(company_id=company_id, id__in=ids).values_list('id', 'name'))


def professional_names(company_id: UUID, ids: set[UUID]) -> dict[UUID, str]:
    if not ids:
        return {}
    return dict(ProfessionalModel.objects.filter(company_id=company_id, id__in=ids).values_list('id', 'name'))


def professional_exists(company_id: UUID, professional_id: UUID) -> bool:
    return ProfessionalModel.objects.filter(company_id=company_id, id=professional_id).exists()
