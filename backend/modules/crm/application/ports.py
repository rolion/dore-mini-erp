from typing import Protocol
from uuid import UUID


class StageCards(Protocol):
    """Tarjetas (oportunidades) ubicadas en una etapa. Las aporta PB-CRM-004; hasta entonces no hay ninguna."""

    def count(self, stage_id: UUID) -> int: ...

    def reassign(self, from_stage_id: UUID, to_stage_id: UUID) -> int: ...
