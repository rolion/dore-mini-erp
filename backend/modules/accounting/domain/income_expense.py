"""Ingresos y egresos por mes (reporte contable). Dominio puro: sin Django.

- Ingreso = Haber − Debe de las cuentas INCOME; Egreso = Debe − Haber de las cuentas EXPENSE y COST.
- Utilidad = Ingreso − Egreso (misma definición que el «Resultado» de `ledger_report`).
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .account_class import COST, EXPENSE, INCOME

ZERO = Decimal('0.00')
EXPENSE_CLASSES = (EXPENSE, COST)


def month_key(day: date) -> str:
    """`yyyy-MM` del mes calendario de una fecha."""
    return f'{day.year:04d}-{day.month:02d}'


def month_keys(start: date, end: date) -> list[str]:
    """Meses calendario que intersectan `[start, end]`, en orden cronológico."""
    keys, year, month = [], start.year, start.month
    while (year, month) <= (end.year, end.month):
        keys.append(f'{year:04d}-{month:02d}')
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return keys


def default_period(periods: list, today: date):
    """Período por defecto: el abierto que contiene hoy; si no, el abierto más reciente; si no, el más reciente."""
    if not periods:
        return None
    open_periods = [p for p in periods if p.is_open]
    for period in open_periods:
        if period.contains(today):
            return period
    pool = open_periods or periods
    return max(pool, key=lambda p: (p.end_date, p.start_date))


@dataclass(frozen=True)
class MonthResult:
    month: str
    income: Decimal
    expense: Decimal

    @property
    def profit(self) -> Decimal:
        return self.income - self.expense


@dataclass(frozen=True)
class IncomeExpenseTotals:
    income: Decimal
    expense: Decimal

    @property
    def profit(self) -> Decimal:
        return self.income - self.expense

    @classmethod
    def of(cls, months: list[MonthResult]) -> 'IncomeExpenseTotals':
        return cls(sum((m.income for m in months), ZERO), sum((m.expense for m in months), ZERO))


def build_months(keys: list[str], sums: list[tuple[str, str | None, Decimal, Decimal]]) -> list[MonthResult]:
    """Una fila por mes de `keys` (con 0 si no hay movimientos) a partir de `(mes, clase, debe, haber)`.

    Las clases distintas de Ingresos, Gastos y Costos (o sin clase) no cuentan.
    """
    income = {key: ZERO for key in keys}
    expense = {key: ZERO for key in keys}
    for key, account_class, debit, credit in sums:
        if key not in income:
            continue
        if account_class == INCOME:
            income[key] += credit - debit
        elif account_class in EXPENSE_CLASSES:
            expense[key] += debit - credit
    return [MonthResult(key, income[key], expense[key]) for key in keys]
