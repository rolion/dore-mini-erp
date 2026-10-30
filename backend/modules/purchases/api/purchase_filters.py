from datetime import date
from uuid import UUID

from rest_framework.exceptions import ValidationError

from modules.purchases.domain.enums import PaymentStatus, PurchaseStatus, ReceptionStatus
from modules.purchases.domain.repositories import PurchaseFilters

PENDING = 'pending'
SEARCH_MAX_LENGTH = 100


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError('Fecha inválida: use el formato AAAA-MM-DD.') from None


def _parse_uuid(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError:
        raise ValueError('Valor inválido: use un identificador.') from None


def _enum(enum_type: type, extra: tuple[str, ...] = ()):
    def parse(raw: str):
        if raw in extra:
            return raw
        try:
            return enum_type(raw)
        except ValueError:
            options = ', '.join([m.value for m in enum_type] + list(extra))
            raise ValueError(f'Valor inválido: use uno de {options}.') from None
    return parse


def parse_purchase_filters(params) -> PurchaseFilters:
    """Convierte los query params de la lista en filtros tipados; un valor inválido da 400 por parámetro."""
    errors: dict[str, list[str]] = {}
    values: dict[str, object] = {}

    def read(name: str, parse) -> None:
        raw = params.get(name)
        if raw is None or raw == '':
            return
        try:
            values[name] = parse(raw)
        except ValueError as exc:
            errors[name] = [str(exc)]

    read('supplier_id', _parse_uuid)
    read('date_from', _parse_date)
    read('date_to', _parse_date)
    read('status', _enum(PurchaseStatus))
    read('reception_status', _enum(ReceptionStatus))
    read('payment_status', _enum(PaymentStatus, extra=(PENDING,)))

    search = (params.get('q') or '').strip()
    if len(search) > SEARCH_MAX_LENGTH:
        errors['q'] = [f'Máximo {SEARCH_MAX_LENGTH} caracteres.']
    if 'date_from' in values and 'date_to' in values and values['date_from'] > values['date_to']:
        errors['date_to'] = ['La fecha final no puede ser anterior a la inicial.']
    if errors:
        raise ValidationError(errors)

    payment = values.get('payment_status')
    return PurchaseFilters(
        supplier_id=values.get('supplier_id'),
        date_from=values.get('date_from'),
        date_to=values.get('date_to'),
        status=values.get('status'),
        reception_status=values.get('reception_status'),
        payment_status=payment if isinstance(payment, PaymentStatus) else None,
        pending_payment=payment == PENDING,
        search=search,
    )
