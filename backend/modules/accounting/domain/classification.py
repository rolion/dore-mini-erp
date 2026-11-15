from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from .account import AccountValidationError, validate_name
from .catalog import DIRECTIONS


class ClassificationNotFound(Exception):
    pass


def validate_direction(direction: object) -> str:
    if not isinstance(direction, str) or direction.strip().upper() not in DIRECTIONS:
        raise AccountValidationError({'direction': [f'La dirección debe ser una de: {", ".join(DIRECTIONS)}.']})
    return direction.strip().upper()


@dataclass
class Classification:
    """Motivo de un movimiento de dinero (por qué), de ingreso o de egreso. La dirección no cambia tras crearla."""
    id: UUID
    name: str
    direction: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, name: object, direction: object) -> 'Classification':
        return cls(id=uuid4(), name=validate_name(name), direction=validate_direction(direction))

    def rename(self, name: object) -> None:
        self.name = validate_name(name)

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False

    def ensure_usable(self, direction: str) -> None:
        """Valida un uso nuevo: activa y de la dirección esperada."""
        if not self.is_active:
            raise AccountValidationError({'classification_id': ['La clasificación está inactiva.']})
        if self.direction != direction:
            raise AccountValidationError({'classification_id': ['La clasificación no es de esa dirección.']})
