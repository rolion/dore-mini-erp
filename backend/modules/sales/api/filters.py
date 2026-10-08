from datetime import date
from uuid import UUID

from rest_framework.exceptions import ValidationError

from modules.sales.domain.enums import OrderStatus, PaymentStatus, SalesChannel
from modules.sales.domain.repositories import (
    BY_EXPECTED_DELIVERY,
    EXPECTED_DELIVERY_DATE,
    NEWEST_FIRST,
    ORDER_DATE,
    OrderFilters,
)


def _enum_list(raw: str, enum_type: type) -> tuple:
    values = []
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            values.append(enum_type(part))
        except ValueError:
            raise ValueError(f'Valor inválido: "{part}".') from None
    return tuple(values)


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError('Fecha inválida: use el formato AAAA-MM-DD.') from None


def parse_order_filters(params) -> OrderFilters:
    """Convierte los query params de la lista en filtros tipados; los valores inválidos dan 400 por parámetro."""
    errors: dict[str, list[str]] = {}
    values: dict[str, object] = {}

    def read(name: str, parse):
        raw = params.get(name)
        if raw is None or raw == '':
            return
        try:
            values[name] = parse(raw)
        except ValueError as exc:
            errors[name] = [str(exc)]

    read('status', lambda raw: _enum_list(raw, OrderStatus))
    read('payment_status', lambda raw: _enum_list(raw, PaymentStatus))
    read('sales_channel', lambda raw: SalesChannel(raw))
    read('customer_id', lambda raw: UUID(raw))
    read('date_from', _parse_date)
    read('date_to', _parse_date)

    def choice(options: tuple[str, ...]):
        def parse(raw: str) -> str:
            if raw not in options:
                raise ValueError(f'Valor inválido: use {" o ".join(options)}.')
            return raw
        return parse

    def boolean(raw: str) -> bool:
        if raw not in ('true', 'false'):
            raise ValueError('Valor inválido: use "true" o "false".')
        return raw == 'true'

    read('date_field', choice((ORDER_DATE, EXPECTED_DELIVERY_DATE)))
    read('has_balance', boolean)
    read('ordering', choice((NEWEST_FIRST, BY_EXPECTED_DELIVERY)))

    if 'date_from' in values and 'date_to' in values and values['date_from'] > values['date_to']:
        errors['date_to'] = ['La fecha final no puede ser anterior a la inicial.']
    if errors:
        raise ValidationError(errors)

    return OrderFilters(
        statuses=values.get('status', ()),
        payment_statuses=values.get('payment_status', ()),
        sales_channel=values.get('sales_channel'),
        customer_id=values.get('customer_id'),
        date_field=values.get('date_field', ORDER_DATE),
        date_from=values.get('date_from'),
        date_to=values.get('date_to'),
        has_balance=values.get('has_balance'),
        ordering=values.get('ordering', NEWEST_FIRST),
    )
