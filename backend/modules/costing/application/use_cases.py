from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from modules.costing.domain.exceptions import (
    AdoptionIdReused,
    NegativeStock,
    StockChanged,
    ValuationAlreadyAdopted,
)
from modules.costing.domain.valuation import ValuationAdoption, parse_lines

ZERO = Decimal('0')


@dataclass(frozen=True)
class WarehouseQuantity:
    warehouse_id: UUID
    warehouse_name: str
    quantity: Decimal


@dataclass(frozen=True)
class ProductStock:
    product_id: UUID
    product_name: str
    unit_abbreviation: str | None
    quantity: Decimal
    warehouses: tuple[WarehouseQuantity, ...]


@dataclass(frozen=True)
class Blocker:
    product_id: UUID
    product_name: str
    warehouse_id: UUID
    warehouse_name: str
    quantity: Decimal


@dataclass(frozen=True)
class Proposal:
    lines: tuple[ProductStock, ...]
    blockers: tuple[Blocker, ...]


class CompanyStock(Protocol):
    """Existencias de la empresa que Costeo lee de Inventario."""

    def locked(self) -> AbstractContextManager[None]: ...

    def snapshot(self) -> list[ProductStock]: ...

    def names(self, product_ids) -> dict[UUID, tuple[str, str | None]]: ...


class AdoptionRepository(Protocol):
    def get(self) -> ValuationAdoption | None: ...

    def save(self, adoption: ValuationAdoption) -> None: ...


def build_proposal(stocks: list[ProductStock]) -> Proposal:
    """Líneas a valorar (saldo total > 0) y bloqueos (cualquier almacén con saldo negativo)."""
    blockers = tuple(
        Blocker(s.product_id, s.product_name, w.warehouse_id, w.warehouse_name, w.quantity)
        for s in stocks for w in s.warehouses if w.quantity < 0)
    blocked = {b.product_id for b in blockers}
    lines = tuple(s for s in stocks if s.quantity > 0 and s.product_id not in blocked)
    return Proposal(lines, blockers)


@dataclass(frozen=True)
class ValuationView:
    adoption: ValuationAdoption | None
    names: dict[UUID, tuple[str, str | None]]


class GetValuation:
    def __init__(self, repository: AdoptionRepository, stock: CompanyStock):
        self.repository = repository
        self.stock = stock

    def execute(self) -> ValuationView:
        adoption = self.repository.get()
        names = self.stock.names([line.product_id for line in adoption.lines]) if adoption else {}
        return ValuationView(adoption, names)


class GetProposal:
    def __init__(self, stock: CompanyStock):
        self.stock = stock

    def execute(self) -> Proposal:
        return build_proposal(self.stock.snapshot())


@dataclass(frozen=True)
class AdoptionOutcome:
    adoption: ValuationAdoption
    names: dict[UUID, tuple[str, str | None]]
    replayed: bool


class AdoptValuation:
    """Adopta la valoración inicial: todo o nada, bajo el bloqueo de los almacenes de la empresa (AC-01..07)."""

    def __init__(self, repository: AdoptionRepository, stock: CompanyStock):
        self.repository = repository
        self.stock = stock

    def execute(self, *, adoption_id: UUID, raw_lines: list[dict], user_id: UUID | None, user_name: str,
                now: datetime) -> AdoptionOutcome:
        lines = parse_lines(raw_lines)  # 400 antes de tocar la base
        with self.stock.locked():
            existing = self.repository.get()
            if existing is not None:
                return self._replay(existing, adoption_id, lines)
            proposal = build_proposal(self.stock.snapshot())
            if proposal.blockers:
                raise NegativeStock(list(proposal.blockers))
            self._check_reconciled(proposal, lines)
            adoption = ValuationAdoption.adopt(adoption_id, now, user_id, user_name, lines)
            self.repository.save(adoption)
        return AdoptionOutcome(adoption, self.stock.names([line.product_id for line in lines]), replayed=False)

    def _replay(self, existing: ValuationAdoption, adoption_id: UUID, lines) -> AdoptionOutcome:
        if existing.id != adoption_id:
            raise ValuationAlreadyAdopted()
        if not existing.same_content_as(lines):
            raise AdoptionIdReused()
        return AdoptionOutcome(existing, self.stock.names([line.product_id for line in existing.lines]),
                               replayed=True)

    @staticmethod
    def _check_reconciled(proposal: Proposal, lines) -> None:
        current = {s.product_id: s.quantity for s in proposal.lines}
        sent = {line.product_id: line.reconciled_quantity for line in lines}
        differences = [(pid, sent.get(pid), current.get(pid)) for pid in sorted(current.keys() | sent.keys(), key=str)
                       if sent.get(pid) != current.get(pid)]
        if differences:
            raise StockChanged(differences)


