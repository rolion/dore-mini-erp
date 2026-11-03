from typing import Protocol
from uuid import UUID

from modules.service_catalog.domain.service import Service, ServiceNotFound, ServiceValidationError


class ServiceRepository(Protocol):
    def get(self, service_id: UUID, *, for_update: bool = False) -> Service | None: ...
    def save(self, service: Service) -> Service: ...
    def list(self, *, search: str = '', active: bool | None = None, specialty_id: str = ''): ...


class SpecialtyDirectory(Protocol):
    def accepts(self, specialty_id: UUID) -> bool: ...


class UnavailableSpecialties:
    """Personal es opcional y aún no está integrado: nunca aceptar una referencia no verificada."""
    def accepts(self, specialty_id: UUID) -> bool:
        return False


class ServiceCatalog:
    def __init__(self, repository: ServiceRepository, specialties: SpecialtyDirectory):
        self.repository = repository
        self.specialties = specialties

    def get(self, service_id: UUID, *, for_update: bool = False) -> Service:
        service = self.repository.get(service_id, for_update=for_update)
        if service is None:
            raise ServiceNotFound
        return service

    def _validate_specialty(self, service: Service) -> None:
        if service.specialty_id is not None and not self.specialties.accepts(service.specialty_id):
            raise ServiceValidationError({'specialty_id': [
                'La especialidad no está disponible en esta empresa. Guarda sin especialidad.'
            ]})

    def create(self, **values) -> Service:
        service = Service.create(**values)
        self._validate_specialty(service)
        return self.repository.save(service)

    def update(self, service_id: UUID, **values) -> Service:
        previous = self.get(service_id, for_update=True)
        service = previous.updated(**values)
        if service.specialty_id != previous.specialty_id:
            self._validate_specialty(service)
        return self.repository.save(service)

    def set_active(self, service_id: UUID, *, active: bool) -> Service:
        service = self.get(service_id, for_update=True)
        if active:
            service.activate()
        else:
            service.deactivate()
        return self.repository.save(service)
