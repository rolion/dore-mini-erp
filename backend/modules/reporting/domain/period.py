"""Periodo de un reporte: día, semana (lunes a domingo), mes o rango explícito. Regla de negocio pura."""
import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


class PeriodKind(str, Enum):
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    RANGE = 'range'


class PeriodError(Exception):
    """Los parámetros de periodo no son válidos; `errors` mapea parámetro -> mensajes."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


@dataclass(frozen=True)
class Period:
    kind: PeriodKind
    date_from: date
    date_to: date


DEFAULT_KIND = PeriodKind.MONTH
_RELATIVE = {PeriodKind.DAY, PeriodKind.WEEK, PeriodKind.MONTH}


def _relative(kind: PeriodKind, today: date) -> Period:
    if kind is PeriodKind.DAY:
        return Period(kind, today, today)
    if kind is PeriodKind.WEEK:
        monday = today - timedelta(days=today.weekday())
        return Period(kind, monday, monday + timedelta(days=6))
    last_day = calendar.monthrange(today.year, today.month)[1]
    return Period(kind, today.replace(day=1), today.replace(day=last_day))


def resolve_period(kind: str | None, date_from: date | None, date_to: date | None, today: date) -> Period:
    """Resuelve el periodo pedido relativo a `today` (fecha local del negocio).

    - `kind` ∈ day | week | month, o ambas fechas (rango inclusivo); por omisión, el mes en curso.
    - No se puede combinar `kind` con fechas ni enviar una sola fecha.
    """
    has_dates = date_from is not None or date_to is not None
    if kind is not None and has_dates:
        raise PeriodError({'period': ['Use period o date_from/date_to, no ambos.']})
    if has_dates:
        errors: dict[str, list[str]] = {}
        if date_from is None:
            errors['date_from'] = ['Indique también la fecha inicial.']
        if date_to is None:
            errors['date_to'] = ['Indique también la fecha final.']
        if errors:
            raise PeriodError(errors)
        if date_from > date_to:
            raise PeriodError({'date_to': ['La fecha final no puede ser anterior a la inicial.']})
        return Period(PeriodKind.RANGE, date_from, date_to)
    if kind is None:
        return _relative(DEFAULT_KIND, today)
    try:
        parsed = PeriodKind(kind)
    except ValueError:
        parsed = None
    if parsed not in _RELATIVE:
        raise PeriodError({'period': ['Valor inválido: use day, week o month.']})
    return _relative(parsed, today)
