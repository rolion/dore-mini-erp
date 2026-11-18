"""Reporte contable del libro (CONT-05): arma flujo, resultado y cobertura. Los repositorios entran por puerto."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from modules.accounting.domain.account_class import ASSET
from modules.accounting.domain.coverage import Period, gaps
from modules.accounting.domain.ledger_report import (
    CashFlow,
    Coverage,
    EntryMoneyLine,
    MoneyAccount,
    ResultSummary,
    build_cash_flow,
    build_coverage,
    build_result,
)
from modules.accounting.domain.trial_balance import AccountMovements

ZERO = Decimal('0.00')


@dataclass(frozen=True)
class LedgerReport:
    date_from: date
    date_to: date
    cash_flow: CashFlow
    result: ResultSummary
    coverage: Coverage


class AccountReader(Protocol):
    def list(self, is_active: bool | None = None, account_class: str | None = None) -> list: ...


class JournalReader(Protocol):
    def movements_by_account(self, date_from: date | None, date_to: date | None,
                             since: date | None = None) -> dict[UUID, AccountMovements]: ...

    def money_lines(self, account_ids: list[UUID], date_from: date, date_to: date) -> list[EntryMoneyLine]: ...


class CoverageReader(Protocol):
    def cutoff_date(self) -> date | None: ...

    def periods(self) -> list[Period]: ...


class GetLedgerReport:
    def __init__(self, accounts: AccountReader, journal: JournalReader, coverage: CoverageReader):
        self.accounts = accounts
        self.journal = journal
        self.coverage = coverage

    def execute(self, date_from: date, date_to: date) -> LedgerReport:
        accounts = self.accounts.list()
        money = [a for a in accounts if a.account_class == ASSET and a.kind is not None]
        cutoff = self.coverage.cutoff_date()
        movements = self.journal.movements_by_account(date_from, date_to, since=cutoff)
        opening = {a.id: movements[a.id].opening_debit - movements[a.id].opening_credit
                   for a in money if a.id in movements}
        start = max(date_from, cutoff or date_from)
        lines = self.journal.money_lines([a.id for a in money], start, date_to) if money else []
        flow = build_cash_flow([MoneyAccount(a.id, a.name) for a in money], opening, lines)
        by_class: dict[str, tuple[Decimal, Decimal]] = {}
        for account in accounts:
            moved = movements.get(account.id)
            if moved is None or account.account_class is None:
                continue
            debit, credit = by_class.get(account.account_class, (ZERO, ZERO))
            by_class[account.account_class] = (debit + moved.debit, credit + moved.credit)
        coverage = build_coverage(cutoff, gaps(self.coverage.periods()), date_from, date_to)
        return LedgerReport(date_from, date_to, flow, build_result(by_class), coverage)
