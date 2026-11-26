from dataclasses import dataclass, replace
from typing import Sequence

from modules.purchases.domain.enums import PaymentStatus, PurchaseStatus
from modules.purchases.domain.repositories import PurchaseFilters, PurchaseRepository, PurchaseSummary, PurchaseTotals


@dataclass(frozen=True)
class PurchasesReportData:
    purchases: Sequence[PurchaseSummary]
    totals: PurchaseTotals


class _PurchasesReport:
    """Reporte de compras de solo lectura: los filtros de la persona (fechas, período fiscal) se combinan con los
    criterios fijos de cada reporte (`scope`), y se devuelven las compras con los totales de todo el conjunto."""

    def __init__(self, purchases: PurchaseRepository):
        self.purchases = purchases

    def scope(self, filters: PurchaseFilters) -> PurchaseFilters:
        raise NotImplementedError

    def execute(self, filters: PurchaseFilters | None = None) -> PurchasesReportData:
        scoped = self.scope(filters or PurchaseFilters())
        return PurchasesReportData(self.purchases.list(filters=scoped), self.purchases.totals(scoped))


class PaidPurchasesReport(_PurchasesReport):
    """Compras pagadas: confirmadas con el pago completo."""

    def scope(self, filters: PurchaseFilters) -> PurchaseFilters:
        return replace(filters, status=PurchaseStatus.CONFIRMED, payment_status=PaymentStatus.PAID,
                       pending_payment=False, supplier_id=None, reception_status=None, search='')


class PayablePurchasesReport(_PurchasesReport):
    """Compras por pagar: confirmadas con pago pendiente (sin pagar o pagadas en parte)."""

    def scope(self, filters: PurchaseFilters) -> PurchaseFilters:
        return replace(filters, status=PurchaseStatus.CONFIRMED, payment_status=None, pending_payment=True,
                       supplier_id=None, reception_status=None, search='')
