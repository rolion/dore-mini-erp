from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from .exceptions import WarehouseConflict, WarehouseValidationError

NAME_MAX_LENGTH = 150
DEFAULT_WAREHOUSE_NAME = 'Almacén principal'


def validate_name(name: object) -> str:
    if not isinstance(name, str) or not name.strip():
        raise WarehouseValidationError({'name': ['El nombre es obligatorio.']})
    name = name.strip()
    if len(name) > NAME_MAX_LENGTH:
        raise WarehouseValidationError({'name': [f'El nombre no puede superar {NAME_MAX_LENGTH} caracteres.']})
    return name


@dataclass
class Warehouse:
    id: UUID
    name: str
    description: str = ''
    active: bool = True
    is_default: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, name: object, description: str | None = '') -> 'Warehouse':
        return cls(id=uuid4(), name=validate_name(name), description=(description or '').strip())

    def rename(self, name: object) -> None:
        self.name = validate_name(name)

    def describe(self, description: str | None) -> None:
        self.description = (description or '').strip()

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        """Desactiva el almacén. Los saldos y recepciones los comprueba el caso de uso (datos de otro contexto)."""
        if self.is_default:
            raise WarehouseConflict(
                'warehouse_is_default',
                'No se puede desactivar el almacén predeterminado; define otro como predeterminado primero.')
        self.active = False

    def make_default(self) -> None:
        if not self.active:
            raise WarehouseConflict('warehouse_inactive', 'Solo un almacén activo puede ser el predeterminado.')
        self.is_default = True
