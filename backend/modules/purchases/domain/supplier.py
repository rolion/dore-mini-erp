import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from .exceptions import SupplierValidationError

NAME_MAX_LENGTH = 150
TAX_ID_MAX_LENGTH = 50
PHONE_MAX_LENGTH = 30
EMAIL_MAX_LENGTH = 254
NOTES_MAX_LENGTH = 2000

_EMAIL_FORMAT = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _fail(field: str, message: str) -> SupplierValidationError:
    return SupplierValidationError({field: [message]})


def validate_name(name: object) -> str:
    if not isinstance(name, str) or not name.strip():
        raise _fail('name', 'El nombre es obligatorio.')
    name = name.strip()
    if len(name) > NAME_MAX_LENGTH:
        raise _fail('name', f'El nombre no puede superar {NAME_MAX_LENGTH} caracteres.')
    return name


def _optional_text(value: object, field: str, label: str, max_length: int) -> str:
    if value is None:
        return ''
    if not isinstance(value, str):
        raise _fail(field, f'{label} debe ser texto.')
    value = value.strip()
    if len(value) > max_length:
        raise _fail(field, f'{label} no puede superar {max_length} caracteres.')
    return value


def validate_tax_id(tax_id: object) -> str:
    return _optional_text(tax_id, 'tax_id', 'La identificación', TAX_ID_MAX_LENGTH)


def validate_phone(phone: object) -> str:
    return _optional_text(phone, 'phone', 'El teléfono', PHONE_MAX_LENGTH)


def validate_notes(notes: object) -> str:
    return _optional_text(notes, 'notes', 'Las notas', NOTES_MAX_LENGTH)


def validate_email(email: object) -> str:
    email = _optional_text(email, 'email', 'El correo', EMAIL_MAX_LENGTH)
    if email and not _EMAIL_FORMAT.match(email):
        raise _fail('email', 'Ingresa un correo válido.')
    return email


def _collect(checks) -> dict[str, str]:
    """Ejecuta validaciones (campo, función) juntando los errores de todos los campos."""
    errors: dict[str, list[str]] = {}
    values: dict[str, str] = {}
    for field, check in checks:
        try:
            values[field] = check()
        except SupplierValidationError as exc:
            errors.update(exc.errors)
    if errors:
        raise SupplierValidationError(errors)
    return values


@dataclass
class Supplier:
    id: UUID
    name: str
    tax_id: str = ''
    phone: str = ''
    email: str = ''
    notes: str = ''
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, name: object, tax_id: object = '', phone: object = '', email: object = '',
               notes: object = '') -> 'Supplier':
        values = _collect((
            ('name', lambda: validate_name(name)),
            ('tax_id', lambda: validate_tax_id(tax_id)),
            ('phone', lambda: validate_phone(phone)),
            ('email', lambda: validate_email(email)),
            ('notes', lambda: validate_notes(notes)),
        ))
        return cls(id=uuid4(), active=True, **values)

    def rename(self, name: object) -> None:
        self.name = validate_name(name)

    def change_tax_id(self, tax_id: object) -> None:
        self.tax_id = validate_tax_id(tax_id)

    def change_contact(self, phone: object, email: object) -> None:
        """Cambia teléfono y correo juntos: si alguno es inválido no se modifica ninguno."""
        values = _collect((
            ('phone', lambda: validate_phone(phone)),
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
