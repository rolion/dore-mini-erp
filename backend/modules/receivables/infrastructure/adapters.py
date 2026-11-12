"""Puente de Cobros hacia las fachadas públicas de las fuentes del compromiso (Cotizaciones y Odontología)."""
from collections.abc import Iterable
from uuid import UUID

from modules.dentistry import services as dental
from modules.quotations import services as quotations
from shared.domain.commitment import CommitmentSnapshot


class CommitmentSource:
    """Lee, bloquea y marca líneas de un tipo de proforma; el módulo concreto se elige por `kind`."""

    def __init__(self, facade, company_id: UUID):
        self._facade = facade
        self.company_id = company_id

    def get(self, number: str) -> CommitmentSnapshot | None:
        return self._facade.get_commitment(self.company_id, number)

    def get_many(self, numbers: Iterable[str]) -> dict[str, CommitmentSnapshot]:
        return self._facade.get_commitments(self.company_id, numbers)

    def lock(self, number: str) -> CommitmentSnapshot | None:
        return self._facade.lock_commitment(self.company_id, number)

    def mark_collected(self, line_ids: Iterable[UUID]) -> None:
        self._facade.mark_lines_collected(self.company_id, line_ids)


_FACADES = {quotations.KIND: quotations, dental.KIND: dental}


def source_for(kind: str, company_id: UUID) -> CommitmentSource | None:
    facade = _FACADES.get(kind)
    return CommitmentSource(facade, company_id) if facade else None
