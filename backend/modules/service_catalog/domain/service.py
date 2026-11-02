from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4


class ServiceValidationError(Exception):
    def __init__(self, errors: dict[str, list[str]]):
        self.errors = errors
        super().__init__(errors)


class ServiceNotFound(Exception):
    pass


@dataclass
class Service:
    id: UUID
    name: str
    base_price: Decimal
    duration_minutes: int
    code: str = ''
    description: str = ''
    specialty_id: UUID | None = None
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, **values) -> 'Service':
        service = cls(uuid4(), '', Decimal('0'), 0)
        return service.updated(**values)

    def updated(self, **values) -> 'Service':
        candidate = replace(self, **values)
        errors: dict[str, list[str]] = {}
        for field, maximum, required in (('name', 150, True), ('code', 50, False),
                                          ('description', 5000, False)):
            raw = getattr(candidate, field)
            if not isinstance(raw, str):
                errors[field] = ['Ingresa un texto válido.']
                continue
            value = raw.strip()
            if field == 'code':
                value = value.upper()
            if required and not value:
                errors[field] = ['El nombre es obligatorio.']
            elif len(value) > maximum:
                errors[field] = [f'No puede superar {maximum} caracteres.']
            setattr(candidate, field, value)
        raw_price = candidate.base_price
        try:
            if isinstance(raw_price, bool) or not isinstance(raw_price, (str, int, Decimal)):
                raise ValueError
            price = Decimal(raw_price)
            if not price.is_finite() or not Decimal('0') <= price <= Decimal('9999999999.99'):
                raise ValueError
            if price != price.quantize(Decimal('0.01')):
                raise ValueError
            candidate.base_price = price.quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError):
            errors['base_price'] = ['Ingresa un precio BOB entre 0 y 9999999999.99, con hasta 2 decimales.']
        duration = candidate.duration_minutes
        if type(duration) is not int or not 1 <= duration <= 2147483647:
            errors['duration_minutes'] = ['Ingresa minutos enteros mayores que cero.']
        if candidate.specialty_id is not None and not isinstance(candidate.specialty_id, UUID):
            errors['specialty_id'] = ['Especialidad inválida.']
        if errors:
            raise ServiceValidationError(errors)
        return candidate

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        self.active = False
