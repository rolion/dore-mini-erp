from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from django.db import IntegrityError, transaction

from ...domain.profiles import Professional, ProfileValidationError, Specialty
from .models import ProfessionalModel, SpecialtyModel


class DjangoProfileRepository:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def rows(self, kind: str):
        model = ProfessionalModel if kind == 'professionals' else SpecialtyModel
        rows = model.objects.filter(company_id=self.company_id)
        return rows.prefetch_related('specialties') if kind == 'professionals' else rows

    def list(self, kind: str, search: str = '', active: bool | None = None, specialty_id: UUID | None = None):
        rows = self.rows(kind).filter(name__icontains=search)
        if active is not None:
            rows = rows.filter(active=active)
        if specialty_id is not None:
            rows = rows.filter(specialties__id=specialty_id, specialties__company_id=self.company_id)
        return rows

    def get(self, kind: str, profile_id: UUID):
        row = self.rows(kind).filter(id=profile_id).first()
        if row is None:
            return None
        values = {'id': row.id, 'name': row.name, 'active': row.active}
        if kind == 'specialties':
            return Specialty(**values)
        return Professional(**values, **{key: getattr(row, key) for key in (
            'identification', 'phone', 'email', 'registration_number', 'user_id')},
            specialty_ids=[item.id for item in row.specialties.all()])

    def specialties_exist(self, ids: list[UUID]) -> bool:
        return SpecialtyModel.objects.filter(company_id=self.company_id, id__in=ids).count() == len(ids)

    def save(self, kind: str, profile: Professional | Specialty, actor_id: int):
        values = asdict(profile)
        values.pop('id')
        specialty_ids = values.pop('specialty_ids', None)
        try:
            with transaction.atomic():
                model = ProfessionalModel if kind == 'professionals' else SpecialtyModel
                row = model.objects.filter(company_id=self.company_id).select_for_update().filter(id=profile.id).first()
                if row is None:
                    row = model(id=profile.id, company_id=self.company_id, created_by=actor_id)
                for key, value in values.items():
                    setattr(row, key, value)
                row.updated_by = actor_id
                row.save()
                if specialty_ids is not None:
                    row.specialties.set(SpecialtyModel.objects.filter(company_id=self.company_id, id__in=specialty_ids))
        except IntegrityError as exc:
            if getattr(getattr(exc.__cause__, 'diag', None), 'constraint_name', None) == 'personnel_user_unique':
                raise ProfileValidationError({'user_id': ['Este usuario ya está vinculado a un profesional.']}) from exc
            raise
        return self.rows(kind).get(id=profile.id)
