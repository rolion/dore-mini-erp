import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from .exceptions import CustomerValidationError

NAME_MAX_LENGTH = 150
PHONE_MAX_LENGTH = 30
EMAIL_MAX_LENGTH = 254
NOTES_MAX_LENGTH = 2000

_PHONE_SEPARATORS = re.compile(r'[\s\-.()]')
_EMAIL_FORMAT = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_MIN_PHONE_DIGITS = 8
_MAX_PHONE_DIGITS = 15


def _fail(field: str, message: str) -> CustomerValidationError:
    return CustomerValidationError({field: [message]})


def normalize_phone(raw: str, default_country_code: str) -> str:
    """Devuelve `+<país><dígitos>` si el número es normalizable; si no, el texto recortado original.

    Es normalizable si queda `+` y de 8 a 15 dígitos. Un número solo de dígitos recibe el código de
    país por defecto; `00` inicial equivale a `+`. No se elimina un `0` inicial de troncal.
    """
    text = raw.strip()
    cleaned = _PHONE_SEPARATORS.sub('', text)
    if cleaned.startswith('+'):
        digits = cleaned[1:]
    elif cleaned.startswith('00'):
        digits = cleaned[2:]
    elif cleaned.isdigit():
        digits = default_country_code + cleaned
    else:
        return text
    if digits.isdigit() and _MIN_PHONE_DIGITS <= len(digits) <= _MAX_PHONE_DIGITS:
        return f'+{digits}'
    return text


def validate_name(name: object) -> str:
    if not isinstance(name, str) or not name.strip():
        raise _fail('name', 'El nombre es obligatorio.')
    name = name.strip()
    if len(name) > NAME_MAX_LENGTH:
        raise _fail('name', f'El nombre no puede superar {NAME_MAX_LENGTH} caracteres.')
    return name


def validate_phone(phone: object, default_country_code: str) -> str:
    if phone is None:
        return ''
    if not isinstance(phone, str):
        raise _fail('phone', 'El teléfono debe ser texto.')
    normalized = normalize_phone(phone, default_country_code)
    if len(normalized) > PHONE_MAX_LENGTH:
        raise _fail('phone', f'El teléfono no puede superar {PHONE_MAX_LENGTH} caracteres.')
    return normalized


def validate_email(email: object) -> str:
    if email is None:
        return ''
    if not isinstance(email, str):
        raise _fail('email', 'El correo debe ser texto.')
    email = email.strip()
    if not email:
        return ''
    if len(email) > EMAIL_MAX_LENGTH:
        raise _fail('email', f'El correo no puede superar {EMAIL_MAX_LENGTH} caracteres.')
    if not _EMAIL_FORMAT.match(email):
        raise _fail('email', 'Ingresa un correo válido.')
    return email


def validate_notes(notes: object) -> str:
    if notes is None:
        return ''
    if not isinstance(notes, str):
        raise _fail('notes', 'Las notas deben ser texto.')
    notes = notes.strip()
    if len(notes) > NOTES_MAX_LENGTH:
        raise _fail('notes', f'Las notas no pueden superar {NOTES_MAX_LENGTH} caracteres.')
    return notes


def _collect(checks) -> dict[str, str]:
    """Ejecuta validaciones (campo, función) juntando los errores de todos los campos."""
    errors: dict[str, list[str]] = {}
    values: dict[str, str] = {}
    for field, check in checks:
        try:
            values[field] = check()
        except CustomerValidationError as exc:
            errors.update(exc.errors)
    if errors:
        raise CustomerValidationError(errors)
    return values


@dataclass
class Customer:
    id: UUID
    name: str
    phone: str = ''
    email: str = ''
    notes: str = ''
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, name: object, default_country_code: str, phone: object = '', email: object = '',
               notes: object = '') -> 'Customer':
        values = _collect((
            ('name', lambda: validate_name(name)),
            ('phone', lambda: validate_phone(phone, default_country_code)),
            ('email', lambda: validate_email(email)),
            ('notes', lambda: validate_notes(notes)),
        ))
        return cls(id=uuid4(), active=True, **values)

    def rename(self, name: object) -> None:
        self.name = validate_name(name)

    def change_contact(self, default_country_code: str, phone: object, email: object) -> None:
        """Cambia teléfono y correo juntos: si alguno es inválido no se modifica ninguno."""
        values = _collect((
            ('phone', lambda: validate_phone(phone, default_country_code)),
            ('email', lambda: validate_email(email)),
        ))
        self.phone = values['phone']
        self.email = values['email']

    def change_notes(self, notes: object) -> None:
        self.notes = validate_notes(notes)

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        self.active = False
