"""Fachada pública: DTO inmutable para snapshots de consumidores futuros; lecturas siempre por empresa."""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from modules.service_catalog.infrastructure.django.repositories import DjangoServiceRepository
from shared import module_gate


@dataclass(frozen=True)
class ServiceSnapshot:
    id: UUID
    name: str
    code: str
    base_price: Decimal
    duration_minutes: int
    active: bool
    specialty_id: UUID | None


def get_service(company_id: UUID, service_id: UUID) -> ServiceSnapshot | None:
    if not module_gate.is_enabled(company_id, 'services'):
        return None
    service = DjangoServiceRepository(company_id).get(service_id)
    if service is None:
        return None
    return ServiceSnapshot(service.id, service.name, service.code, service.base_price,
                           service.duration_minutes, service.active, service.specialty_id)


def get_service_for_new_use(company_id: UUID, service_id: UUID) -> ServiceSnapshot | None:
    service = get_service(company_id, service_id)
    return service if service and service.active else None
