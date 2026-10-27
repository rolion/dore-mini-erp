from typing import Protocol
from uuid import UUID


class WarehouseActivity(Protocol):
    """Datos de otros contextos que impiden desactivar un almacén (saldos, recepciones pendientes)."""

    def has_nonzero_balance(self, warehouse_id: UUID) -> bool: ...

    def has_pending_receipts(self, warehouse_id: UUID) -> bool: ...
