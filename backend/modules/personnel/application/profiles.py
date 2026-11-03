from typing import Protocol
from uuid import UUID

from ..domain.profiles import Professional, ProfileNotFound, ProfileValidationError, Specialty


class ProfileRepository(Protocol):
    def get(self, kind: str, profile_id: UUID) -> Professional | Specialty | None: ...
    def save(self, kind: str, profile: Professional | Specialty, actor_id: int): ...
    def specialties_exist(self, ids: list[UUID]) -> bool: ...


class UserDirectory(Protocol):
    def exists(self, user_id: int) -> bool: ...


class SaveProfile:
    def __init__(self, repository: ProfileRepository, users: UserDirectory):
        self.repository = repository
        self.users = users

    def execute(self, kind: str, values: dict, actor_id: int, profile_id: UUID | None = None):
        profile = self.repository.get(kind, profile_id) if profile_id else (
            Professional() if kind == 'professionals' else Specialty())
        if profile is None:
            raise ProfileNotFound()
        profile.edit(values)
        if isinstance(profile, Professional):
            if profile.user_id is not None and not self.users.exists(profile.user_id):
                raise ProfileValidationError({'user_id': ['Usuario no disponible en esta empresa.']})
            if not self.repository.specialties_exist(profile.specialty_ids):
                raise ProfileValidationError({'specialty_ids': ['Especialidad no disponible en esta empresa.']})
        return self.repository.save(kind, profile, actor_id)


class ChangeProfileState:
    def __init__(self, repository: ProfileRepository):
        self.repository = repository

    def execute(self, kind: str, profile_id: UUID, active: bool, actor_id: int):
        profile = self.repository.get(kind, profile_id)
        if profile is None:
            raise ProfileNotFound()
        profile.activate() if active else profile.deactivate()
        return self.repository.save(kind, profile, actor_id)
