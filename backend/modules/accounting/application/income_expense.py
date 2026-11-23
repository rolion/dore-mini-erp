"""Ingresos y egresos por mes de un período fiscal. Sin Django: los repositorios entran por puerto."""
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from modules.accounting.domain.account import AccountValidationError
from modules.accounting.domain.income_expense import (
    IncomeExpenseTotals,
    MonthResult,
    build_months,
    default_period,
    month_keys,
)

MONTH_PATTERN = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


class PeriodReader(Protocol):
    def all(self) -> list: ...

    def get(self, period_id: UUID): ...


class ResultByMonthReader(Protocol):
    def result_by_month(self, date_from: date, date_to: date) -> list[tuple[str, str | None, Decimal, Decimal]]: ...


@dataclass(frozen=True)
class IncomeExpenseReport:
    period: object | None
    months: list[MonthResult]
    totals: IncomeExpenseTotals


class GetIncomeExpense:
    def __init__(self, periods: PeriodReader, journal: ResultByMonthReader):
        self.periods = periods
        self.journal = journal

    def execute(self, today: date, period_id: UUID | None = None,
                months: list[str] | None = None) -> IncomeExpenseReport:
        period = self._period(today, period_id)
        if period is None:
            return IncomeExpenseReport(None, [], IncomeExpenseTotals.of([]))
        keys = month_keys(period.start_date, period.end_date)
        selected = self._selected(keys, months)
        sums = self.journal.result_by_month(period.start_date, period.end_date)
        rows = build_months(selected, sums)
        return IncomeExpenseReport(period, rows, IncomeExpenseTotals.of(rows))

    def _period(self, today: date, period_id: UUID | None):
        if period_id is None:
            return default_period(self.periods.all(), today)
        period = self.periods.get(period_id)
        if period is None:
            raise AccountValidationError({'period_id': ['El período no existe en esta empresa.']})
        return period

    @staticmethod
    def _selected(keys: list[str], months: list[str] | None) -> list[str]:
        if not months:
            return keys
        bad = [m for m in months if not MONTH_PATTERN.match(m) or m not in keys]
        if bad:
            names = ', '.join(sorted(set(bad)))
            raise AccountValidationError({'months': [f'Mes fuera del período o inválido: {names}.']})
        return [key for key in keys if key in set(months)]
