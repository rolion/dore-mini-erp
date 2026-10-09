from datetime import date
from uuid import UUID

from rest_framework.exceptions import ValidationError

from modules.expenses.domain.enums import ExpenseStatus
from modules.expenses.domain.repositories import ExpenseFilters

_STATUS_OPTIONS = {'active': ExpenseStatus.ACTIVE, 'voided': ExpenseStatus.VOIDED, 'all': None}


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError('Fecha inválida: use el formato AAAA-MM-DD.') from None


def _parse_uuid(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError:
        raise ValueError('Valor inválido: use un identificador de categoría.') from None


def parse_expense_filters(params) -> ExpenseFilters:
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

    def status(raw: str):
        if raw not in _STATUS_OPTIONS:
            raise ValueError('Valor inválido: use active, voided o all.')
        return _STATUS_OPTIONS[raw]

    read('date_from', _parse_date)
    read('date_to', _parse_date)
    read('category_id', _parse_uuid)
    read('status', status)

    if 'date_from' in values and 'date_to' in values and values['date_from'] > values['date_to']:
        errors['date_to'] = ['La fecha final no puede ser anterior a la inicial.']
    if errors:
        raise ValidationError(errors)

    return ExpenseFilters(
        date_from=values.get('date_from'),
        date_to=values.get('date_to'),
        category_id=values.get('category_id'),
        status=values['status'] if 'status' in values else ExpenseStatus.ACTIVE,
    )
