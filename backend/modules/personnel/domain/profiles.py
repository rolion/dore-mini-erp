"""Perfiles de atención: independientes de las cuentas y de sus permisos."""
import re
from dataclasses import dataclass, field
from uuid import UUID, uuid4


class ProfileValidationError(Exception):
    def __init__(self, errors: dict[str, list[str]]):
        self.errors = errors


class ProfileNotFound(Exception):
    pass


def text(value: object, field_name: str, maximum: int, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ProfileValidationError({field_name: ['Debe ser texto.']})
    value = value.strip()
    if required and not value:
        raise ProfileValidationError({field_name: ['El nombre es obligatorio.']})
    if len(value) > maximum:
        raise ProfileValidationError({field_name: [f'No puede superar {maximum} caracteres.']})
    return value


@dataclass
class Profile:
    id: UUID = field(default_factory=uuid4)
    name: str = ''
    active: bool = True

    def edit(self, values: dict) -> None:
        self.name = text(values.get('name', self.name), 'name', 150, required=True)

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        self.active = False


@dataclass
class Specialty(Profile):
    pass


@dataclass
class Professional(Profile):
    identification: str = ''
    phone: str = ''
    email: str = ''
    registration_number: str = ''
    user_id: int | None = None
    specialty_ids: list[UUID] = field(default_factory=list)

    def edit(self, values: dict) -> None:
        # Validar todo antes de mutar: una edición inválida no cambia parte del perfil.
        cleaned = {'name': text(values.get('name', self.name), 'name', 150, required=True)}
        for key, maximum in (('identification', 50), ('phone', 30), ('email', 254), ('registration_number', 100)):
            cleaned[key] = text(values.get(key, getattr(self, key)), key, maximum)
        if cleaned['email'] and not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', cleaned['email']):
            raise ProfileValidationError({'email': ['Ingresa un correo válido.']})
        for key, value in cleaned.items():
            setattr(self, key, value)
        if 'user_id' in values:
            self.user_id = values['user_id']
        if 'specialty_ids' in values:
            self.specialty_ids = list(dict.fromkeys(values['specialty_ids']))
