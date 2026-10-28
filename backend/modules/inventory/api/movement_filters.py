from datetime import date
from uuid import UUID

from rest_framework.exceptions import ValidationError

from modules.inventory.domain.movement import SOURCE_TYPES, MovementKind
from modules.inventory.domain.repositories import MovementFilters


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


def _parse_kind(raw: str) -> MovementKind:
    try:
        return MovementKind(raw)
    except ValueError:
        raise ValueError('Valor inválido: use in o out.') from None


def _parse_source_type(raw: str) -> str:
    if raw != 'none' and raw not in SOURCE_TYPES:
        raise ValueError('Valor inválido: use none o una clase de origen conocida.')
    return raw


def parse_movement_filters(params) -> MovementFilters:
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

    read('date_from', _parse_date)
    read('date_to', _parse_date)
    read('product_id', _parse_uuid)
    read('warehouse_id', _parse_uuid)
    read('kind', _parse_kind)
    read('source_type', _parse_source_type)

    if 'date_from' in values and 'date_to' in values and values['date_from'] > values['date_to']:
        errors['date_to'] = ['La fecha final no puede ser anterior a la inicial.']
    if errors:
        raise ValidationError(errors)
    return MovementFilters(**values)
