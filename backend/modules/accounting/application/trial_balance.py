"""Sumas y saldos (CONT-04): una fila por cuenta de la empresa con sus filtros. Sin Django: los repositorios entran por puerto."""
from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from modules.accounting.domain.account import AccountValidationError
from modules.accounting.domain.account_class import validate_account_class
from modules.accounting.domain.trial_balance import AccountMovements, TrialBalanceRow, TrialBalanceTotals


@dataclass(frozen=True)
class TrialBalanceFilters:
    """Filtros opcionales; `period_id` equivale a los límites de ese período y excluye a las fechas sueltas."""
    period_id: UUID | None = None
    date_from: date | None = None
    date_to: date | None = None
    account_class: str | None = None
    account_id: UUID | None = None


@dataclass(frozen=True)
class TrialBalance:
    date_from: date | None
    date_to: date | None
    rows: list[TrialBalanceRow]
    totals: TrialBalanceTotals


class AccountReader(Protocol):
    def list(self, is_active: bool | None = None, account_class: str | None = None) -> list: ...

    def get(self, account_id: UUID): ...


class MovementsReader(Protocol):
    def movements_by_account(self, date_from: date | None, date_to: date | None) -> dict[UUID, AccountMovements]: ...


class PeriodReader(Protocol):
    def get(self, period_id: UUID): ...


class GetTrialBalance:
    def __init__(self, accounts: AccountReader, journal: MovementsReader, periods: PeriodReader):
        self.accounts = accounts
        self.journal = journal
        self.periods = periods

    def execute(self, filters: TrialBalanceFilters) -> TrialBalance:
        date_from, date_to = self._range(filters)
        account_class = validate_account_class(filters.account_class) if filters.account_class else None
        accounts = self.accounts.list(account_class=account_class)
        if filters.account_id is not None:
            if self.accounts.get(filters.account_id) is None:
                raise AccountValidationError({'account_id': ['La cuenta no existe en esta empresa.']})
            accounts = [a for a in accounts if a.id == filters.account_id]
        movements = self.journal.movements_by_account(date_from, date_to)
        rows = [TrialBalanceRow.build(account, movements.get(account.id)) for account in accounts]
        return TrialBalance(date_from, date_to, rows, TrialBalanceTotals.of(rows))

    def _range(self, filters: TrialBalanceFilters) -> tuple[date | None, date | None]:
        if filters.period_id is not None:
            if filters.date_from or filters.date_to:
                raise AccountValidationError({'period_id': ['No se puede combinar el período con fechas.']})
            period = self.periods.get(filters.period_id)
            if period is None:
                raise AccountValidationError({'period_id': ['El período no existe en esta empresa.']})
            return period.start_date, period.end_date
        if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
            raise AccountValidationError({'date_from': ['La fecha inicial no puede ser posterior a la final.']})
        return filters.date_from, filters.date_to
