from collections.abc import Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from modules.costing.domain.cost import (
    ZERO,
    CostEvent,
    CostKind,
    CostUnavailable,
    weighted_average,
)
from modules.costing.domain.valuation import ValuationAdoption


class CostEventRepository(Protocol):
    def get(self, kind: CostKind, source_type: str, source_id: str, product_id: UUID) -> CostEvent | None: ...

    def list_for_source(self, kind: CostKind, source_type: str, source_id: str) -> list[CostEvent]: ...

    def latest_averages(self, product_ids: Iterable[UUID]) -> dict[UUID, Decimal]: ...

    def add(self, event: CostEvent) -> CostEvent: ...


class AdoptionReader(Protocol):
    def get(self) -> ValuationAdoption | None: ...


class StockTotals(Protocol):
    """Saldos de Inventario que Costeo lee; el bloqueo serializa recepciones y salidas de la empresa."""

    def locked(self) -> AbstractContextManager[None]: ...

    def totals(self, product_ids: Iterable[UUID]) -> dict[UUID, Decimal]: ...


@dataclass(frozen=True)
class CostedOutput:
    lines: tuple[CostEvent, ...]
    total: Decimal


class _CostBase:
    def __init__(self, events: CostEventRepository, adoption: AdoptionReader, stock: StockTotals):
        self.events = events
        self.adoption = adoption
        self.stock = stock

    def current_averages(self, product_ids: list[UUID], adoption: ValuationAdoption | None) -> dict[UUID, Decimal]:
        """Promedio vigente: el de la última recepción o, si no hay, el costo unitario de la valoración inicial."""
        averages = {line.product_id: line.unit_cost for line in (adoption.lines if adoption else ())
                    if line.product_id in product_ids}
        averages.update(self.events.latest_averages(product_ids))
        return averages


class CostReceipt(_CostBase):
    """Actualiza el promedio con una recepción (no genera asiento: el de recepción es de Compras)."""

    def execute(self, source_type: str, source_id: str, lines: list[tuple[UUID, Decimal, Decimal]],
                occurred_at: datetime) -> bool:
        adoption = self.adoption.get()
        if adoption is None or not lines:
            return False
        with self.stock.locked():
            product_ids = [product_id for product_id, _, _ in lines]
            balances = self.stock.totals(product_ids)  # ya incluyen la entrada de esta recepción
            averages = self.current_averages(product_ids, adoption)
            for product_id, quantity, unit_cost in lines:
                if self.events.get(CostKind.IN, source_type, source_id, product_id) is not None:
                    continue  # reintento idempotente
                previous = balances.get(product_id, ZERO) - quantity
                average = weighted_average(previous, averages.get(product_id), quantity, unit_cost)
                self.events.add(CostEvent.receipt(source_type, source_id, product_id, quantity, unit_cost, average,
                                                  occurred_at))
                averages[product_id] = average
                balances[product_id] = previous + quantity
        return True


class ReverseReceiptCost(_CostBase):
    """Contra-evento de cada recepción costeada: conserva el costo original y el vínculo; no cambia el promedio."""

    def execute(self, source_type: str, source_id: str, occurred_at: datetime) -> None:
        originals = self.events.list_for_source(CostKind.IN, source_type, source_id)
        if not originals:
            return
        with self.stock.locked():
            averages = self.events.latest_averages([event.product_id for event in originals])
            for original in originals:
                if self.events.get(CostKind.IN_REVERSAL, source_type, source_id, original.product_id) is not None:
                    continue
                self.events.add(original.reversal(averages.get(original.product_id, original.average_after),
                                                  occurred_at))


class ReverseOutputCost(_CostBase):
    """Contra-evento de cada salida valorizada (devolución): conserva el costo de venta y el vínculo; idempotente."""

    def execute(self, source_type: str, source_id: str, occurred_at: datetime) -> None:
        originals = self.events.list_for_source(CostKind.OUT, source_type, source_id)
        if not originals:
            return
        with self.stock.locked():
            for original in originals:
                if self.events.get(CostKind.OUT_REVERSAL, source_type, source_id, original.product_id) is None:
                    self.events.add(original.output_reversal(occurred_at))


class CostOutputs(_CostBase):
    """Valoriza las salidas de un documento al promedio vigente: todas o ninguna, idempotente por origen."""

    def execute(self, source_type: str, source_id: str, lines: list[tuple[UUID, Decimal]],
                occurred_at: datetime) -> CostedOutput:
        adoption = self.adoption.get()
        if adoption is None:
            raise CostUnavailable(CostUnavailable.NOT_ADOPTED)
        with self.stock.locked():
            product_ids = [product_id for product_id, _ in lines]
            averages = self.current_averages(product_ids, adoption)
            missing = [pid for pid in product_ids if pid not in averages
                       and self.events.get(CostKind.OUT, source_type, source_id, pid) is None]
            if missing:
                raise CostUnavailable(CostUnavailable.NO_AVERAGE, missing)  # antes de escribir nada
            costed: list[CostEvent] = []
            for product_id, quantity in lines:
                existing = self.events.get(CostKind.OUT, source_type, source_id, product_id)
                costed.append(existing or self.events.add(
                    CostEvent.output(source_type, source_id, product_id, quantity, averages[product_id],
                                     occurred_at)))
        return CostedOutput(tuple(costed), sum((event.total_cost for event in costed), ZERO))
