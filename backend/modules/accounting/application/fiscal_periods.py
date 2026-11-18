from datetime import datetime
from typing import Protocol
from uuid import UUID

from modules.accounting.domain.fiscal_period import (
    FiscalPeriod,
    FiscalPeriodConflict,
    FiscalPeriodNotFound,
)


class PeriodUsage(Protocol):
    """Puerto: cuántos asientos hoy dentro del período quedarían fuera del rango propuesto (los aporta el motor de asientos)."""

    def entries_outside(self, company_id: UUID, period_id: UUID, start_date, end_date) -> int: ...


def _require(periods, period_id: UUID, *, for_update: bool = False) -> FiscalPeriod:
    period = periods.get_for_update(period_id) if for_update else periods.get(period_id)
    if period is None:
        raise FiscalPeriodNotFound(str(period_id))
    return period


def _check_overlap(periods, period: FiscalPeriod) -> None:
    others = periods.overlapping(period.start_date, period.end_date, period.id)
    if others:
        names = [o.name for o in others]
        raise FiscalPeriodConflict(
            'period_overlap', f'El rango se superpone con: {", ".join(names)}.', names)


class ListFiscalPeriods:
    def __init__(self, periods):
        self.periods = periods

    def execute(self) -> list[FiscalPeriod]:
        return self.periods.all()


class GetFiscalPeriod:
    def __init__(self, periods):
        self.periods = periods

    def execute(self, period_id: UUID) -> FiscalPeriod:
        return _require(self.periods, period_id)


class CreateFiscalPeriod:
    def __init__(self, periods):
        self.periods = periods

    def execute(self, name: object, start_date: object, end_date: object) -> FiscalPeriod:
        period = FiscalPeriod.create(name, start_date, end_date)
        self.periods.lock_company()
        _check_overlap(self.periods, period)
        return self.periods.save(period)


class UpdateFiscalPeriod:
    def __init__(self, periods, usage: PeriodUsage):
        self.periods = periods
        self.usage = usage

    def execute(self, period_id: UUID, name: object = None, start_date: object = None, end_date: object = None
                ) -> FiscalPeriod:
        self.periods.lock_company()
        period = _require(self.periods, period_id, for_update=True)
        if name is not None:
            period.rename(name)
        if start_date is not None or end_date is not None:
            previous = (period.start_date, period.end_date)
            period.change_limits(start_date if start_date is not None else period.start_date,
                                 end_date if end_date is not None else period.end_date)
            if (period.start_date, period.end_date) != previous:
                _check_overlap(self.periods, period)
                outside = self.usage.entries_outside(self.periods.company_id, period.id, period.start_date, period.end_date)
                if outside:
                    raise FiscalPeriodConflict(
                        'period_has_entries',
                        f'No se pueden cambiar los límites: {outside} asiento(s) del período quedarían fuera de él.')
        return self.periods.save(period)


class CloseFiscalPeriod:
    """Solo cambia el estado: cerrar no genera asientos de cierre de resultados."""

    def __init__(self, periods):
        self.periods = periods

    def execute(self, period_id: UUID, by: str, at: datetime) -> FiscalPeriod:
        period = _require(self.periods, period_id, for_update=True)
        period.close(by, at)
        return self.periods.save(period)


class ReopenFiscalPeriod:
    def __init__(self, periods):
        self.periods = periods

    def execute(self, period_id: UUID, by: str, at: datetime) -> FiscalPeriod:
        period = _require(self.periods, period_id, for_update=True)
        period.reopen(by, at)
        return self.periods.save(period)
