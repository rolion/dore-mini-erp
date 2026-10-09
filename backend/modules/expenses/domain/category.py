from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from .validation import required_text

NAME_MAX_LENGTH = 100


def validate_name(name: object) -> str:
    return required_text(name, 'name', 'El nombre', NAME_MAX_LENGTH)


@dataclass
class ExpenseCategory:
    id: UUID
    name: str
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, name: object) -> 'ExpenseCategory':
        return cls(id=uuid4(), name=validate_name(name))

    def rename(self, name: object) -> None:
        self.name = validate_name(name)

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        self.active = False
