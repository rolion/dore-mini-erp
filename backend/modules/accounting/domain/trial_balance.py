"""Sumas y saldos por cuenta (CONT-04). Dominio puro: sin Django.

El saldo de una cuenta sale solo de su Debe y su Haber; nunca de su clasificación.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

ZERO = Decimal('0.00')


def split_balance(debit: Decimal, credit: Decimal) -> tuple[Decimal, Decimal]:
    """(saldo deudor, saldo acreedor) = (max(Debe − Haber, 0), max(Haber − Debe, 0))."""
    return max(debit - credit, ZERO), max(credit - debit, ZERO)


@dataclass(frozen=True)
class AccountMovements:
    """Importes de una cuenta: acumulado anterior al inicio del rango y movimientos del rango."""
    opening_debit: Decimal = ZERO
    opening_credit: Decimal = ZERO
    debit: Decimal = ZERO
    credit: Decimal = ZERO


@dataclass(frozen=True)
class TrialBalanceRow:
    account_id: UUID
    code: str | None
    name: str
    account_class: str | None
    is_active: bool
    opening_debit_balance: Decimal
    opening_credit_balance: Decimal
    debit: Decimal
    credit: Decimal
    debit_balance: Decimal
    credit_balance: Decimal

    @classmethod
    def build(cls, account, movements: AccountMovements | None) -> 'TrialBalanceRow':
        """Fila de una cuenta; sin movimientos todo vale cero."""
        m = movements or AccountMovements()
        opening_debit_balance, opening_credit_balance = split_balance(m.opening_debit, m.opening_credit)
        debit_balance, credit_balance = split_balance(m.opening_debit + m.debit, m.opening_credit + m.credit)
        return cls(account.id, account.code, account.name, account.account_class, account.is_active,
                   opening_debit_balance, opening_credit_balance, m.debit, m.credit, debit_balance, credit_balance)


@dataclass(frozen=True)
class TrialBalanceTotals:
    opening_debit_balance: Decimal
    opening_credit_balance: Decimal
    debit: Decimal
    credit: Decimal
    debit_balance: Decimal
    credit_balance: Decimal

    @property
    def balanced(self) -> bool:
        """Debe = Haber y saldos deudores = acreedores (con todas las cuentas incluidas, siempre se cumple)."""
        return self.debit == self.credit and self.debit_balance == self.credit_balance

    @classmethod
    def of(cls, rows: list[TrialBalanceRow]) -> 'TrialBalanceTotals':
        def total(name: str) -> Decimal:
            return sum((getattr(row, name) for row in rows), ZERO)
        return cls(total('opening_debit_balance'), total('opening_credit_balance'), total('debit'), total('credit'),
                   total('debit_balance'), total('credit_balance'))
