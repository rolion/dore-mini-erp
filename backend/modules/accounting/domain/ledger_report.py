"""Reporte contable del libro (CONT-05): flujo de dinero y resultado. Dominio puro: sin Django.

- Flujo = variación (Debe − Haber) de las cuentas de dinero. Por asiento, el neto de sus líneas de dinero decide si es
  una entrada (> 0), una salida (< 0) o una transferencia interna (= 0), que no suma a entradas ni a salidas.
- Resultado = Ingresos − Costos − Gastos, por clasificación de la cuenta (las cuentas correctoras quedan netas).
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from .account_class import COST, EXPENSE, INCOME
from .coverage import Gap

ZERO = Decimal('0.00')


@dataclass(frozen=True)
class MoneyAccount:
    account_id: UUID
    name: str


@dataclass(frozen=True)
class EntryMoneyLine:
    """Neto (Debe − Haber) de una cuenta de dinero dentro de un asiento."""
    entry_id: UUID
    account_id: UUID
    net: Decimal


@dataclass(frozen=True)
class AccountFlow:
    account_id: UUID
    name: str
    opening: Decimal
    net: Decimal
    closing: Decimal


@dataclass(frozen=True)
class CashFlow:
    opening: Decimal
    inflow: Decimal
    outflow: Decimal
    net: Decimal
    closing: Decimal
    transfers: Decimal  # importe movido entre cuentas propias; informativo
    accounts: tuple[AccountFlow, ...]


@dataclass(frozen=True)
class ResultSummary:
    income: Decimal
    cost: Decimal
    margin: Decimal
    expense: Decimal
    result: Decimal


@dataclass(frozen=True)
class Coverage:
    cutoff_date: date | None
    partial: bool


def build_cash_flow(accounts: list[MoneyAccount], opening: dict[UUID, Decimal],
                    lines: list[EntryMoneyLine]) -> CashFlow:
    """`opening`: Debe − Haber acumulado antes del rango por cuenta; `lines`: netos del rango por asiento y cuenta."""
    by_entry: dict[UUID, Decimal] = defaultdict(lambda: ZERO)
    positives: dict[UUID, Decimal] = defaultdict(lambda: ZERO)
    net_by_account: dict[UUID, Decimal] = defaultdict(lambda: ZERO)
    for line in lines:
        by_entry[line.entry_id] += line.net
        net_by_account[line.account_id] += line.net
        if line.net > 0:
            positives[line.entry_id] += line.net
    inflow = sum((n for n in by_entry.values() if n > 0), ZERO)
    outflow = sum((-n for n in by_entry.values() if n < 0), ZERO)
    transfers = sum((positives[e] for e, n in by_entry.items() if n == 0), ZERO)
    rows = tuple(AccountFlow(a.account_id, a.name, opening.get(a.account_id, ZERO), net_by_account[a.account_id],
                             opening.get(a.account_id, ZERO) + net_by_account[a.account_id]) for a in accounts)
    total_opening = sum((r.opening for r in rows), ZERO)
    return CashFlow(total_opening, inflow, outflow, inflow - outflow, total_opening + inflow - outflow, transfers, rows)


def build_result(totals_by_class: dict[str, tuple[Decimal, Decimal]]) -> ResultSummary:
    """`totals_by_class`: clasificación -> (Debe, Haber) del rango."""
    def side(code: str) -> tuple[Decimal, Decimal]:
        return totals_by_class.get(code, (ZERO, ZERO))

    income = side(INCOME)[1] - side(INCOME)[0]
    cost = side(COST)[0] - side(COST)[1]
    expense = side(EXPENSE)[0] - side(EXPENSE)[1]
    margin = income - cost
    return ResultSummary(income, cost, margin, expense, margin - expense)


def build_coverage(cutoff: date | None, gaps: list[Gap], date_from: date, date_to: date) -> Coverage:
    """Parcial si el rango empieza antes del corte, no hay corte o cruza un hueco de cobertura."""
    partial = cutoff is None or date_from < cutoff or any(g.from_on <= date_to and g.to_on > date_from for g in gaps)
    return Coverage(cutoff, partial)
