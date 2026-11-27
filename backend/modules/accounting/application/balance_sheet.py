"""Balance general: lee cuentas y movimientos y arma el estado. Sin Django: los repositorios entran por puerto."""
from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from modules.accounting.domain.account import AccountValidationError
from modules.accounting.domain.balance_sheet import BalanceSheet, build_balance_sheet
from modules.accounting.domain.trial_balance import AccountMovements


@dataclass(frozen=True)
class BalanceSheetFilters:
    date_from: date | None = None
    date_to: date | None = None


@dataclass(frozen=True)
class BalanceSheetReport:
    date_from: date | None
    date_to: date | None
    sheet: BalanceSheet


class AccountReader(Protocol):
    def list(self, is_active: bool | None = None, account_class: str | None = None) -> list: ...


class MovementsReader(Protocol):
    def movements_by_account(self, date_from: date | None, date_to: date | None) -> dict[UUID, AccountMovements]: ...


class GetBalanceSheet:
    def __init__(self, accounts: AccountReader, journal: MovementsReader):
        self.accounts = accounts
        self.journal = journal

    def execute(self, filters: BalanceSheetFilters) -> BalanceSheetReport:
        if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
            raise AccountValidationError({'date_from': ['La fecha inicial no puede ser posterior a la final.']})
        movements = self.journal.movements_by_account(filters.date_from, filters.date_to)
        sheet = build_balance_sheet(self.accounts.list(), movements)
        return BalanceSheetReport(filters.date_from, filters.date_to, sheet)
