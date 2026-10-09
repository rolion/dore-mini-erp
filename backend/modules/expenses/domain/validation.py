"""Validadores de campo compartidos por los agregados del módulo; cada uno lanza `ExpenseValidationError`."""
import re
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from shared.domain.money import DECIMALS, MONEY_MAX, NEGATIVE, TOO_LARGE, InvalidMoney, parse_money

from .exceptions import ExpenseValidationError

_MONEY_MESSAGES = {
    NEGATIVE: '{label} debe ser mayor a cero.',
    DECIMALS: '{label} admite como máximo 2 decimales.',
    TOO_LARGE: '{label} no puede superar ' + str(MONEY_MAX) + '.',
}


# Un monto escrito como texto debe ser un decimal plano: `Decimal()` también acepta `1e3`, `1_000` o `Infinity`,
# que no son importes (el signo se deja pasar para que `parse_money` lo informe como negativo).
_PLAIN_DECIMAL = re.compile(r'-?[0-9]+(\.[0-9]+)?')


def fail(field_name: str, message: str) -> ExpenseValidationError:
    return ExpenseValidationError({field_name: [message]})


def required_text(value: object, field_name: str, label: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise fail(field_name, f'{label} es obligatorio.' if label.startswith('El ') else f'{label} es obligatoria.')
    return optional_text(value, field_name, label, max_length)


def optional_text(value: object, field_name: str, label: str, max_length: int) -> str:
    if value is None:
        return ''
    if not isinstance(value, str):
        raise fail(field_name, f'{label} debe ser texto.')
    value = value.strip()
    if len(value) > max_length:
        raise fail(field_name, f'{label} no puede superar {max_length} caracteres.')
    return value


def positive_money(value: object, field_name: str, label: str) -> Decimal:
    if isinstance(value, str) and not _PLAIN_DECIMAL.fullmatch(value.strip()):
        raise fail(field_name, f'{label} debe ser un número decimal.')
    try:
        amount = parse_money(value)
    except InvalidMoney as exc:
        message = _MONEY_MESSAGES.get(exc.code, '{label} debe ser un número decimal.')
        raise fail(field_name, message.format(label=label)) from None
    if amount <= 0:
        raise fail(field_name, f'{label} debe ser mayor a cero.')
    return amount


def required_date(value: object, field_name: str, label: str) -> date:
    if value is None:
        raise fail(field_name, f'{label} es obligatoria.')
    if isinstance(value, datetime) or not isinstance(value, date):
        raise fail(field_name, f'{label} debe ser una fecha válida.')
    return value


def required_uuid(value: object, field_name: str, label: str) -> UUID:
    if value is None:
        raise fail(field_name, f'{label} es obligatoria.')
    if not isinstance(value, UUID):
        raise fail(field_name, f'{label} no es válida.')
    return value


def run_checks(checks: list[tuple[str, Callable[[], object]]]) -> tuple[dict[str, object], dict[str, list[str]]]:
    """Ejecuta todas las validaciones y junta los errores de todos los campos."""
    values: dict[str, object] = {}
    errors: dict[str, list[str]] = {}
    for name, check in checks:
        try:
            values[name] = check()
        except ExpenseValidationError as exc:
            errors.update(exc.errors)
    return values, errors
