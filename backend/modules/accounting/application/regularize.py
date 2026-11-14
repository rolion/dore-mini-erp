"""Caso de uso de PB-ACC-004: previsualizar y aplicar la regularización de pagos históricos en el libro."""
from dataclasses import replace
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from modules.accounting.domain.entry import Entry
from modules.accounting.domain.regularization import (
    ALREADY_EXISTED,
    CREATED,
    FAILED,
    MISSING,
    HistoricalMapping,
    Item,
    Report,
    RegularizationInputError,
    SourcePayment,
    classify,
)

ORIGINS = ('PRODUCT', 'SERVICE')


class PaymentSource(Protocol):
    def list_payments(self, company_id: UUID, date_from: date | None, date_to: date | None) -> list[SourcePayment]: ...


class LedgerRejected(Exception):
    """El libro rechazó la entrada (validación o conflicto)."""


class RegularizationInProgress(Exception):
    """Otra regularización de la misma empresa está corriendo."""


class RegularizationLedger(Protocol):
    def entries_by_origin(self, company_id: UUID, origin_kind: str, ids: list[UUID]) -> dict[UUID, Entry]: ...

    def try_lock(self, company_id: UUID) -> bool: ...

    def unlock(self, company_id: UUID) -> None: ...

    def create(self, company_id: UUID, item: Item, regularized_at: datetime, executed_by: str) -> bool:
        """Crea la entrada en su propia transacción; `False` si ya existía. Lanza `LedgerRejected`."""


class RegularizeLedger:
    def __init__(self, sources: dict[str, PaymentSource], ledger: RegularizationLedger):
        self.sources = sources
        self.ledger = ledger

    def plan(self, company_id: UUID, date_from: date | None, date_to: date | None,
             mapping: HistoricalMapping) -> Report:
        """Previsualización: lee y compara; nunca escribe."""
        if date_from and date_to and date_from > date_to:
            raise RegularizationInputError(['--from no puede ser posterior a --to.'])
        items: list[Item] = []
        for origin_kind in ORIGINS:
            source = self.sources.get(origin_kind)
            if source is None:
                continue
            payments = source.list_payments(company_id, date_from, date_to)
            existing = self.ledger.entries_by_origin(company_id, origin_kind, [p.id for p in payments])
            items.extend(classify(p, existing.get(p.id), mapping) for p in payments)
        return Report(items)

    def apply(self, company_id: UUID, date_from: date | None, date_to: date | None, mapping: HistoricalMapping,
              executed_by: str, now: datetime) -> Report:
        """Recalcula el plan y crea solo los faltantes elegibles; un fallo no detiene los demás."""
        if not self.ledger.try_lock(company_id):
            raise RegularizationInProgress('Ya hay una regularización en curso para esta empresa.')
        try:
            report = self.plan(company_id, date_from, date_to, mapping)
            applied: list[Item] = []
            for item in report.items:
                if item.status != MISSING:
                    applied.append(item)
                    continue
                try:
                    created = self.ledger.create(company_id, item, now, executed_by)
                    applied.append(replace(item, outcome=CREATED if created else ALREADY_EXISTED))
                except LedgerRejected as exc:
                    applied.append(replace(item, outcome=FAILED, error=str(exc)))
            return Report(applied)
        finally:
            self.ledger.unlock(company_id)
