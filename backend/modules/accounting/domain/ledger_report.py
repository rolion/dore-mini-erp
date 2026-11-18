"""Reporte contable del libro (CONT-05): flujo de dinero y resultado. Dominio puro: sin Django.

- Flujo = variación (Debe − Haber) de las cuentas de dinero. Por asiento, el neto de sus líneas de dinero decide si es
  una entrada (> 0), una salida (< 0) o una transferencia interna (= 0), que no suma a entradas ni a salidas.
- Resultado = Ingresos − Costos − Gastos, por clasificación de la cuenta (las cuentas correctoras quedan netas).
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_DOWN, Decimal
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


INFLOW, OUTFLOW, TRANSFER_IN, TRANSFER_OUT = 'inflow', 'outflow', 'transfer_in', 'transfer_out'
CENT = Decimal('0.01')


@dataclass(frozen=True)
class AccountFlow:
    account_id: UUID
    name: str
    opening: Decimal
    net: Decimal
    closing: Decimal
    inflow: Decimal = ZERO  # entradas externas
    outflow: Decimal = ZERO  # salidas externas
    transfers_in: Decimal = ZERO
    transfers_out: Decimal = ZERO


@dataclass(frozen=True)
class MoneyMovement:
    """Parte de un asiento que mueve una cuenta de dinero: `amount` siempre positivo, `kind` dice el sentido."""
    entry_id: UUID
    account_id: UUID
    kind: str
    amount: Decimal


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


def _share(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Reparte `total` en proporción a `weights` con centavos exactos; el resto va a la primera (la mayor)."""
    whole = sum(weights, ZERO)
    shares = [(total * w / whole).quantize(CENT, rounding=ROUND_DOWN) for w in weights]
    shares[0] += total - sum(shares, ZERO)
    return shares


def classify_entry(entry_id: UUID, nets: dict[UUID, Decimal], names: dict[UUID, str]) -> list[MoneyMovement]:
    """Clasifica un asiento por sus netos (Debe − Haber) en cuentas de dinero (INV-02 e INV-04).

    Neto 0 = transferencia pura. Con ambos signos y neto ≠ 0, `min(Σ positivas, Σ |negativas|)` es transferencia
    (recibida y enviada) y el resto del lado dominante es entrada o salida externa.
    """
    def ordered(sign: int) -> list[tuple[UUID, Decimal]]:
        rows = [(a, abs(n)) for a, n in nets.items() if n * sign > 0]
        return sorted(rows, key=lambda r: (-r[1], names.get(r[0], ''), str(r[0])))

    positives, negatives = ordered(1), ordered(-1)
    received = sum((n for _, n in positives), ZERO)
    sent = sum((n for _, n in negatives), ZERO)
    transfer = min(received, sent)
    moves: list[MoneyMovement] = []

    def emit(rows: list[tuple[UUID, Decimal]], transfer_kind: str, external_kind: str) -> None:
        in_transfer = _share(transfer, [n for _, n in rows]) if transfer and rows else [ZERO] * len(rows)
        for (account_id, amount), moved in zip(rows, in_transfer):
            if moved:
                moves.append(MoneyMovement(entry_id, account_id, transfer_kind, moved))
            if amount - moved:
                moves.append(MoneyMovement(entry_id, account_id, external_kind, amount - moved))

    emit(positives, TRANSFER_IN, INFLOW)
    emit(negatives, TRANSFER_OUT, OUTFLOW)
    return moves


def build_cash_flow_movements(lines: list[EntryMoneyLine], names: dict[UUID, str]) -> list[MoneyMovement]:
    """Todas las partes de movimiento de las líneas del rango, agrupadas por asiento."""
    by_entry: dict[UUID, dict[UUID, Decimal]] = defaultdict(dict)
    for line in lines:
        by_entry[line.entry_id][line.account_id] = by_entry[line.entry_id].get(line.account_id, ZERO) + line.net
    moves: list[MoneyMovement] = []
    for entry_id, nets in by_entry.items():
        moves.extend(classify_entry(entry_id, nets, names))
    return moves


def build_cash_flow(accounts: list[MoneyAccount], opening: dict[UUID, Decimal],
                    lines: list[EntryMoneyLine]) -> CashFlow:
    """`opening`: Debe − Haber acumulado antes del rango por cuenta; `lines`: netos del rango por asiento y cuenta."""
    net_by_account: dict[UUID, Decimal] = defaultdict(lambda: ZERO)
    for line in lines:
        net_by_account[line.account_id] += line.net
    totals: dict[tuple[UUID, str], Decimal] = defaultdict(lambda: ZERO)
    for move in build_cash_flow_movements(lines, {a.account_id: a.name for a in accounts}):
        totals[(move.account_id, move.kind)] += move.amount
    inflow = sum((v for (_, k), v in totals.items() if k == INFLOW), ZERO)
    outflow = sum((v for (_, k), v in totals.items() if k == OUTFLOW), ZERO)
    transfers = sum((v for (_, k), v in totals.items() if k == TRANSFER_IN), ZERO)
    rows = tuple(AccountFlow(
        a.account_id, a.name, opening.get(a.account_id, ZERO), net_by_account[a.account_id],
        opening.get(a.account_id, ZERO) + net_by_account[a.account_id],
        totals[(a.account_id, INFLOW)], totals[(a.account_id, OUTFLOW)],
        totals[(a.account_id, TRANSFER_IN)], totals[(a.account_id, TRANSFER_OUT)]) for a in accounts)
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
