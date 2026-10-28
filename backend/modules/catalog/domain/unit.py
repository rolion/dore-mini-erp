from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from .exceptions import UnitInUse, UnitValidationError

NAME_MAX_LENGTH = 100
ABBREVIATION_MAX_LENGTH = 10


def _fail(field: str, message: str) -> UnitValidationError:
    return UnitValidationError({field: [message]})


def _validate_text(field: str, label: str, value: object, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _fail(field, f'{label} es obligatorio.')
    value = value.strip()
    if len(value) > max_length:
        raise _fail(field, f'{label} no puede superar {max_length} caracteres.')
    return value


def validate_name(name: object) -> str:
    return _validate_text('name', 'El nombre', name, NAME_MAX_LENGTH)


def validate_abbreviation(abbreviation: object) -> str:
    return _validate_text('abbreviation', 'La abreviatura', abbreviation, ABBREVIATION_MAX_LENGTH)


@dataclass
class UnitOfMeasure:
    id: UUID
    name: str
    abbreviation: str
    allows_fractions: bool = False
    active: bool = True
    # Informativo: lo calcula la persistencia (algún producto la tiene como unidad base).
    in_use: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, name: object, abbreviation: object, allows_fractions: bool = False) -> 'UnitOfMeasure':
        errors: dict[str, list[str]] = {}
        validated: dict[str, str] = {}
        for field, validator, raw in (('name', validate_name, name), ('abbreviation', validate_abbreviation, abbreviation)):
            try:
                validated[field] = validator(raw)
            except UnitValidationError as exc:
                errors.update(exc.errors)
        if errors:
            raise UnitValidationError(errors)
        return cls(id=uuid4(), name=validated['name'], abbreviation=validated['abbreviation'],
                   allows_fractions=bool(allows_fractions))

    def redefine(self, name: object, abbreviation: object, allows_fractions: bool) -> bool:
        """Cambia su definición; con la unidad en uso no se permite modificar su significado. Devuelve si cambió."""
        errors: dict[str, list[str]] = {}
        new_name = self.name
        new_abbreviation = self.abbreviation
        for field, validator, raw in (('name', validate_name, name), ('abbreviation', validate_abbreviation, abbreviation)):
            try:
                value = validator(raw)
            except UnitValidationError as exc:
                errors.update(exc.errors)
                continue
            if field == 'name':
                new_name = value
            else:
                new_abbreviation = value
        if errors:
            raise UnitValidationError(errors)
        new_fractions = bool(allows_fractions)
        changed = (new_name, new_abbreviation, new_fractions) != (self.name, self.abbreviation, self.allows_fractions)
        if changed and self.in_use:
            raise UnitInUse()
        self.name, self.abbreviation, self.allows_fractions = new_name, new_abbreviation, new_fractions
        return changed

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        self.active = False
