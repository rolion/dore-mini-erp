from uuid import UUID


class NoCards:
    """Adaptador vigente mientras no existan tarjetas (PB-CRM-004 lo reemplaza): cuenta 0 y no mueve nada."""

    def count(self, stage_id: UUID) -> int:
        return 0

    def reassign(self, from_stage_id: UUID, to_stage_id: UUID) -> int:
        return 0
