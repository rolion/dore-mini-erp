"""Balance general (Activo, Pasivo, Patrimonio) sobre el libro de asientos. Dominio puro: sin Django.

- Activo = Debe − Haber; Pasivo y Patrimonio = Haber − Debe (una cuenta de saldo contrario sale negativa y resta).
- Saldo final = saldo inicial (antes de «Desde») + movimiento (dentro del rango).
- El Patrimonio suma además el resultado (Ingresos − Costos − Gastos) anterior a «Desde» y el del rango, para que la
  ecuación Activo = Pasivo + Patrimonio cuadre con cualquier rango.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from .account_class import ASSET, COST, EQUITY, EXPENSE, INCOME, LIABILITY
from .trial_balance import AccountMovements

ZERO = Decimal('0.00')
SECTION_KEYS = (ASSET, LIABILITY, EQUITY)


@dataclass(frozen=True)
class Amounts:
    opening: Decimal = ZERO
    movement: Decimal = ZERO

    @property
    def closing(self) -> Decimal:
        return self.opening + self.movement

    @property
    def is_zero(self) -> bool:
        return self.opening == ZERO and self.movement == ZERO and self.closing == ZERO


@dataclass(frozen=True)
class BalanceRow:
    account_id: UUID
    code: str | None
    name: str
    is_active: bool
    amounts: Amounts


@dataclass(frozen=True)
class BalanceSection:
    key: str
    rows: tuple[BalanceRow, ...]
    total: Amounts
    previous_result: Amounts | None = None  # solo Patrimonio
    period_result: Amounts | None = None  # solo Patrimonio


@dataclass(frozen=True)
class BalanceTotals:
    assets: Decimal
    liabilities: Decimal
    equity: Decimal
    unclassified_balance: Decimal

    @property
    def liabilities_and_equity(self) -> Decimal:
        return self.liabilities + self.equity

    @property
    def difference(self) -> Decimal:
        return self.assets - self.liabilities_and_equity

    @property
    def balanced(self) -> bool:
        return self.difference == ZERO


@dataclass(frozen=True)
class BalanceSheet:
    sections: tuple[BalanceSection, ...]
    totals: BalanceTotals


def _net(debit: Decimal, credit: Decimal, account_class: str) -> Decimal:
    return debit - credit if account_class == ASSET else credit - debit


def _result(accounts: list, movements: dict[UUID, AccountMovements]) -> tuple[Decimal, Decimal]:
    """(resultado anterior a «Desde», resultado del rango) = Ingresos − Costos − Gastos."""
    before, within = ZERO, ZERO
    for account in accounts:
        m = movements.get(account.id)
        if m is None or account.account_class not in (INCOME, COST, EXPENSE):
            continue
        # Ingresos suman por Haber − Debe; Costos y Gastos restan por Debe − Haber: en todos los casos Haber − Debe.
        before += m.opening_credit - m.opening_debit
        within += m.credit - m.debit
    return before, within


def build_balance_sheet(accounts: list, movements: dict[UUID, AccountMovements]) -> BalanceSheet:
    """`accounts`: cuentas de la empresa (id, code, name, account_class, is_active); `movements`: por cuenta."""
    rows: dict[str, list[BalanceRow]] = {key: [] for key in SECTION_KEYS}
    unclassified = ZERO
    for account in accounts:
        m = movements.get(account.id) or AccountMovements()
        if account.account_class is None:
            unclassified += (m.opening_debit + m.debit) - (m.opening_credit + m.credit)
        if account.account_class not in rows:
            continue
        cls = account.account_class
        amounts = Amounts(_net(m.opening_debit, m.opening_credit, cls), _net(m.debit, m.credit, cls))
        if not amounts.is_zero:
            rows[cls].append(BalanceRow(account.id, account.code, account.name, account.is_active, amounts))
    previous, within = _result(accounts, movements)
    previous_result, period_result = Amounts(previous, ZERO), Amounts(ZERO, within)

    sections = []
    for key in SECTION_KEYS:
        ordered = tuple(sorted(rows[key], key=lambda r: (r.code or '', r.name)))
        extra = (previous_result, period_result) if key == EQUITY else ()
        parts = [r.amounts for r in ordered] + list(extra)
        total = Amounts(sum((p.opening for p in parts), ZERO), sum((p.movement for p in parts), ZERO))
        sections.append(BalanceSection(key, ordered, total, *(extra or (None, None))))
    totals = BalanceTotals(sections[0].total.closing, sections[1].total.closing, sections[2].total.closing,
                           unclassified)
    return BalanceSheet(tuple(sections), totals)
