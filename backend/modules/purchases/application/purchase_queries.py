from dataclasses import dataclass, field
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from modules.purchases.domain.exceptions import PurchaseNotFound
from modules.purchases.domain.purchase import Purchase
from modules.purchases.domain.repositories import (
    PurchaseFilters,
    PurchaseRepository,
    PaymentRepository,
    PurchaseSummary,
    ReceiptRepository,
    SupplierRepository,
)
from modules.purchases.domain.supplier import Supplier


@dataclass(frozen=True)
class PurchaseDetail:
    """La compra con su proveedor actual (puede estar inactivo; `None` solo si el dato no existiera)."""

    purchase: Purchase
    supplier: Supplier | None
    received: dict[UUID, Decimal] = field(default_factory=dict)  # acumulado confirmado por línea
    paid_total: Decimal = Decimal('0.00')  # suma de pagos confirmados

    @property
    def balance(self) -> Decimal:
        return self.purchase.total - self.paid_total


class GetPurchase:
    def __init__(self, purchases: PurchaseRepository, suppliers: SupplierRepository,
                 receipts: ReceiptRepository | None = None, payments: PaymentRepository | None = None):
        self.purchases = purchases
        self.suppliers = suppliers
        self.receipts = receipts
        self.payments = payments

    def execute(self, purchase_id: UUID) -> PurchaseDetail:
        purchase = self.purchases.get(purchase_id)
        if purchase is None:
            raise PurchaseNotFound(purchase_id)
        return self.detail(purchase)

    def detail(self, purchase: Purchase) -> PurchaseDetail:
        totals = self.receipts.received_totals(purchase.id) if self.receipts is not None else {}
        received = {item.id: totals.get(item.id, Decimal('0')) for item in purchase.items}
        paid = self.payments.paid_total(purchase.id) if self.payments is not None else Decimal('0.00')
        return PurchaseDetail(purchase, self.suppliers.get(purchase.supplier_id), received, paid)


class ListPurchases:
    def __init__(self, purchases: PurchaseRepository):
        self.purchases = purchases

    def execute(self, supplier_id: UUID | None = None,
                filters: PurchaseFilters | None = None) -> Sequence[PurchaseSummary]:
        return self.purchases.list(supplier_id=supplier_id, filters=filters)
