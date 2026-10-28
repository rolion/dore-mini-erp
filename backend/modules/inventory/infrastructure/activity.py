from uuid import UUID

from .django.movement_repository import DjangoStockMovementRepository


class LedgerWarehouseActivity:
    """Actividad de un almacén de la empresa: el saldo sale del libro de movimientos.

    Las recepciones pendientes llegan con su historia; mientras tanto ningún almacén las tiene.
    """

    def __init__(self, company_id: UUID):
        self.movements = DjangoStockMovementRepository(company_id)

    def has_nonzero_balance(self, warehouse_id: UUID) -> bool:
        return self.movements.has_nonzero_balance(warehouse_id)

    def has_pending_receipts(self, warehouse_id: UUID) -> bool:
        return False
