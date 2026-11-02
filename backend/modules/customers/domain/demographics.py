"""Datos administrativos del cliente; nunca contiene información clínica."""
from dataclasses import dataclass
from datetime import date


class DemographicsInvalid(Exception):
    def __init__(self, errors: dict[str, list[str]]):
        self.errors = errors


@dataclass(frozen=True)
class Demographics:
    birth_date: date | None = None
    responsible_name: str = ''
    responsible_phone: str = ''

    @classmethod
    def validated(cls, birth_date: date | None, responsible_name: str,
                  responsible_phone: str, today: date) -> 'Demographics':
        name, phone = responsible_name.strip(), responsible_phone.strip()
        errors = {}
        if birth_date and birth_date > today:
            errors['birth_date'] = ['La fecha de nacimiento no puede ser futura.']
        minor = birth_date is not None and (
            today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day)) < 18)
        if (minor or phone) and not name:
            errors['responsible_name'] = ['Indica el nombre del responsable.']
        if (minor or name) and not phone:
            errors['responsible_phone'] = ['Indica el teléfono del responsable.']
        if len(name) > 150:
            errors['responsible_name'] = ['Máximo 150 caracteres.']
        if len(phone) > 30:
            errors['responsible_phone'] = ['Máximo 30 caracteres.']
        if errors:
            raise DemographicsInvalid(errors)
        return cls(birth_date, name, phone)

    def snapshot(self) -> dict:
        return {'birth_date': self.birth_date.isoformat() if self.birth_date else None,
                'responsible_name': self.responsible_name, 'responsible_phone': self.responsible_phone}
