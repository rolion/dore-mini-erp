"""Detalle de movimientos del flujo de dinero (CONT-14): reutiliza la clasificación de CONT-05. Sin Django."""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from modules.accounting.domain.account_class import ASSET
from modules.accounting.domain.ledger_report import (
    INFLOW,
    OUTFLOW,
    TRANSFER_IN,
    TRANSFER_OUT,
    EntryMoneyLine,
    build_cash_flow_movements,
)

ZERO = Decimal('0.00')
TYPE_KINDS = {'inflow': (INFLOW,), 'outflow': (OUTFLOW,), 'transfer': (TRANSFER_IN, TRANSFER_OUT)}


class CashFlowAccountNotFound(Exception):
    """La cuenta pedida no es una cuenta de dinero de la empresa."""


@dataclass(frozen=True)
class EntryHeader:
    entry_id: UUID
    accounting_date: date
    created_at: datetime
    description: str
    origin_kind: str | None
    origin_id: UUID | None
    is_reversal: bool


@dataclass(frozen=True)
class MovementRow:
    entry: EntryHeader
    account_id: UUID
    account_name: str
    kind: str
    amount: Decimal


@dataclass(frozen=True)
class MovementTotals:
    inflow: Decimal
    outflow: Decimal
    transfers_in: Decimal
    transfers_out: Decimal


@dataclass(frozen=True)
class CashFlowMovements:
    rows: tuple[MovementRow, ...]
    totals: MovementTotals


class AccountReader(Protocol):
    def list(self, is_active: bool | None = None, account_class: str | None = None) -> list: ...


class JournalReader(Protocol):
    def money_lines(self, account_ids: list[UUID], date_from: date, date_to: date) -> list[EntryMoneyLine]: ...

    def money_entries(self, entry_ids: list[UUID]) -> dict[UUID, EntryHeader]: ...


class CoverageReader(Protocol):
    def cutoff_date(self) -> date | None: ...


class ListCashFlowMovements:
    def __init__(self, accounts: AccountReader, journal: JournalReader, coverage: CoverageReader):
        self.accounts = accounts
        self.journal = journal
        self.coverage = coverage

    def execute(self, date_from: date, date_to: date, account_id: UUID | None = None,
                movement_type: str | None = None) -> CashFlowMovements:
        money = {a.id: a.name for a in self.accounts.list() if a.account_class == ASSET and a.kind is not None}
        if account_id is not None and account_id not in money:
            raise CashFlowAccountNotFound(str(account_id))
        cutoff = self.coverage.cutoff_date()
        start = max(date_from, cutoff or date_from)
        lines = self.journal.money_lines(list(money), start, date_to) if money and start <= date_to else []
        kinds = TYPE_KINDS.get(movement_type or '')
        moves = [m for m in build_cash_flow_movements(lines, money)
                 if (account_id is None or m.account_id == account_id) and (kinds is None or m.kind in kinds)]
        headers = self.journal.money_entries(list({m.entry_id for m in moves}))
        rows = sorted((MovementRow(headers[m.entry_id], m.account_id, money[m.account_id], m.kind, m.amount)
                       for m in moves),
                      key=lambda r: (r.entry.accounting_date, r.entry.created_at, str(r.entry.entry_id),
                                     r.account_name, r.kind), reverse=True)
        return CashFlowMovements(tuple(rows), _totals(rows))


def _totals(rows) -> MovementTotals:
    def total(kind: str) -> Decimal:
        return sum((r.amount for r in rows if r.kind == kind), ZERO)

    return MovementTotals(total(INFLOW), total(OUTFLOW), total(TRANSFER_IN), total(TRANSFER_OUT))
