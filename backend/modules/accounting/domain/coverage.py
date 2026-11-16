"""Fecha de corte y cobertura de Contabilidad por empresa (puro: sin Django)."""
from dataclasses import dataclass
from datetime import date

from .account import AccountValidationError


class AccountingSettingsMissing(Exception):
    """La empresa no tiene ajustes de Contabilidad todavía (módulo nunca habilitado)."""


def validate_cutoff(value: object, today: date) -> date:
    if not isinstance(value, date) or hasattr(value, 'hour'):
        raise AccountValidationError({'cutoff_date': ['La fecha de corte no es válida.']})
    if value > today:
        raise AccountValidationError({'cutoff_date': ['La fecha de corte no puede ser futura.']})
    return value


@dataclass(frozen=True)
class Period:
    """Tramo en que Contabilidad estuvo habilitada: `[started_on, ended_on)`; `ended_on` nulo = vigente."""
    started_on: date
    ended_on: date | None = None


@dataclass(frozen=True)
class Gap:
    """Tramo sin cobertura entre una deshabilitación y la siguiente habilitación: `[from_on, to_on)`."""
    from_on: date
    to_on: date


def gaps(periods: list[Period]) -> list[Gap]:
    ordered = sorted(periods, key=lambda p: p.started_on)
    found = []
    for previous, following in zip(ordered, ordered[1:]):
        if previous.ended_on is not None and previous.ended_on < following.started_on:
            found.append(Gap(previous.ended_on, following.started_on))
    return found


@dataclass(frozen=True)
class CoverageStatus:
    """¿Una operación con esa fecha efectiva debe crear movimiento? `reason` explica un «no»."""
    enabled: bool
    cutoff_date: date | None
    covered: bool
    reason: str | None = None  # accounting_disabled | before_cutoff | in_gap


def coverage_status(*, enabled: bool, cutoff_date: date | None, periods: list[Period],
                    effective_date: date) -> CoverageStatus:
    if not enabled or cutoff_date is None:
        return CoverageStatus(enabled, cutoff_date, False, 'accounting_disabled')
    if effective_date < cutoff_date:
        return CoverageStatus(enabled, cutoff_date, False, 'before_cutoff')
    if any(gap.from_on <= effective_date < gap.to_on for gap in gaps(periods)):
        return CoverageStatus(enabled, cutoff_date, False, 'in_gap')
    return CoverageStatus(enabled, cutoff_date, True)
