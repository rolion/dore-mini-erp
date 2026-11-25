"""Prospecto: persona interesada que aún no es cliente (puro: sin Django). INV-04 del PLAN."""
import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from .errors import CrmConflict, CrmValidationError

# Mismos límites que Clientes: al convertir, el prospecto se vuelve cliente sin recortes.
NAME_MAX = 150
PHONE_MAX = 30
EMAIL_MAX = 254
_EMAIL_FORMAT = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ''


def clean_contact(name: object, phone: object, email: object) -> tuple[str, str, str]:
    """Valida nombre (obligatorio), teléfono y correo juntando los errores de todos los campos."""
    errors: dict[str, list[str]] = {}
    name, phone, email = _text(name), _text(phone), _text(email)
    if not name:
        errors['name'] = ['Ingresa un nombre.']
    elif len(name) > NAME_MAX:
        errors['name'] = [f'Usa como máximo {NAME_MAX} caracteres.']
    if len(phone) > PHONE_MAX:
        errors['phone'] = [f'Usa como máximo {PHONE_MAX} caracteres.']
    if len(email) > EMAIL_MAX:
        errors['email'] = [f'Usa como máximo {EMAIL_MAX} caracteres.']
    elif email and not _EMAIL_FORMAT.match(email):
        errors['email'] = ['Ingresa un correo válido.']
    if errors:
        raise CrmValidationError(errors)
    return name, phone, email


@dataclass
class Lead:
    id: UUID
    name: str
    phone: str = ''
    normalized_phone: str = ''
    email: str = ''
    converted_customer_id: UUID | None = None
    created_at: datetime | None = None

    @classmethod
    def create(cls, name: object, phone: object = '', email: object = '', normalized_phone: str = '') -> 'Lead':
        """`normalized_phone` lo calcula Clientes (misma normalización); vacío si no hay teléfono."""
        name, phone, email = clean_contact(name, phone, email)
        return cls(id=uuid4(), name=name, phone=phone, email=email, normalized_phone=normalized_phone if phone else '')

    @property
    def is_converted(self) -> bool:
        return self.converted_customer_id is not None

    def edit(self, name: object, phone: object, email: object, normalized_phone: str) -> None:
        self.name, self.phone, self.email = clean_contact(name, phone, email)
        self.normalized_phone = normalized_phone if self.phone else ''

    def convert_to(self, customer_id: UUID) -> bool:
        """Enlaza el prospecto a un cliente una sola vez; repetir con el mismo cliente no cambia nada."""
        if self.converted_customer_id == customer_id:
            return False
        if self.converted_customer_id is not None:
            raise CrmConflict('already_converted', 'El prospecto ya se convirtió en otro cliente.',
                              customer_id=str(self.converted_customer_id))
        self.converted_customer_id = customer_id
        return True
