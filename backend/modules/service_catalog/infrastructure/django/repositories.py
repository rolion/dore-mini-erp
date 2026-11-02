from dataclasses import fields
from uuid import UUID

from django.db import IntegrityError, transaction

from modules.service_catalog.domain.service import Service, ServiceValidationError

from .models import ServiceModel


def to_entity(model: ServiceModel) -> Service:
    return Service(**{field.name: getattr(model, field.name) for field in fields(Service)})


class ServiceList:
    def __init__(self, queryset):
        self.queryset = queryset

    def count(self):
        return self.queryset.count()

    def __len__(self):
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [to_entity(model) for model in self.queryset[index]]
        return to_entity(self.queryset[index])


class DjangoServiceRepository:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _services(self):
        return ServiceModel.objects.filter(company_id=self.company_id)

    def get(self, service_id: UUID, *, for_update: bool = False) -> Service | None:
        queryset = self._services()
        if for_update:
            queryset = queryset.select_for_update()
        model = queryset.filter(pk=service_id).first()
        return to_entity(model) if model else None

    def save(self, service: Service) -> Service:
        values = {field.name: getattr(service, field.name) for field in fields(Service)
                  if field.name not in ('id', 'created_at', 'updated_at')}
        try:
            # Savepoint permits translating a concurrent unique violation without poisoning the request transaction.
            with transaction.atomic():
                model, _ = ServiceModel.objects.update_or_create(
                    company_id=self.company_id, pk=service.id, defaults=values)
        except IntegrityError as exc:
            if getattr(getattr(exc.__cause__, 'diag', None), 'constraint_name', None) != 'service_company_code_unique':
                raise
            raise ServiceValidationError({'code': ['Ya existe un servicio con este código en tu empresa.']}) from exc
        return to_entity(model)

    def list(self, *, search: str = '', active: bool | None = None, specialty_id: str = '') -> ServiceList:
        queryset = self._services().order_by('name', 'id')
        if search:
            queryset = queryset.filter(name__icontains=search)
        if active is not None:
            queryset = queryset.filter(active=active)
        if specialty_id == 'none':
            queryset = queryset.filter(specialty_id__isnull=True)
        elif specialty_id:
            queryset = queryset.filter(specialty_id=specialty_id)
        return ServiceList(queryset)
