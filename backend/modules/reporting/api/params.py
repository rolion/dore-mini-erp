from datetime import date

from rest_framework.exceptions import ValidationError

from modules.reporting.application.queries import PeriodParams


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError('Fecha inválida: use el formato AAAA-MM-DD.') from None


def parse_period_params(params) -> PeriodParams:
    """Lee `period`, `date_from` y `date_to`; el formato inválido da 400 por parámetro.

    Las combinaciones (ambos a la vez, una sola fecha, rango invertido) las valida el dominio del periodo.
    """
    errors: dict[str, list[str]] = {}
    dates: dict[str, date] = {}
    for name in ('date_from', 'date_to'):
        raw = params.get(name)
        if raw is None or raw == '':
            continue
        try:
            dates[name] = _parse_date(raw)
        except ValueError as exc:
            errors[name] = [str(exc)]
    if errors:
        raise ValidationError(errors)
    kind = params.get('period') or None
    return PeriodParams(kind=kind, date_from=dates.get('date_from'), date_to=dates.get('date_to'))
