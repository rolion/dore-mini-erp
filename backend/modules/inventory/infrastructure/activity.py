from uuid import UUID

from modules.inventory.infrastructure.django.models import StockBalanceModel


class NoWarehouseActivity:
    """Adaptador nulo (sin saldos ni recepciones); queda para pruebas y entornos sin datos de existencias."""

    def has_nonzero_balance(self, warehouse_id: UUID) -> bool:
        return False

    def has_pending_receipts(self, warehouse_id: UUID) -> bool:
        return False


class DjangoWarehouseActivity:
    """Saldos reales de la empresa. Las recepciones pendientes no existen todavía: siempre «no»."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def has_nonzero_balance(self, warehouse_id: UUID) -> bool:
        return StockBalanceModel.objects.filter(
            company_id=self.company_id, warehouse_id=warehouse_id).exclude(quantity=0).exists()

    def has_pending_receipts(self, warehouse_id: UUID) -> bool:
        return False
