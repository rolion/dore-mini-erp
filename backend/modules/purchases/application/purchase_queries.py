from dataclasses import dataclass
from typing import Sequence
from uuid import UUID

from modules.purchases.domain.exceptions import PurchaseNotFound
from modules.purchases.domain.purchase import Purchase
from modules.purchases.domain.repositories import PurchaseRepository, PurchaseSummary, SupplierRepository
from modules.purchases.domain.supplier import Supplier


@dataclass(frozen=True)
class PurchaseDetail:
    """La compra con su proveedor actual (puede estar inactivo; `None` solo si el dato no existiera)."""

    purchase: Purchase
    supplier: Supplier | None


class GetPurchase:
    def __init__(self, purchases: PurchaseRepository, suppliers: SupplierRepository):
        self.purchases = purchases
        self.suppliers = suppliers

    def execute(self, purchase_id: UUID) -> PurchaseDetail:
        purchase = self.purchases.get(purchase_id)
        if purchase is None:
            raise PurchaseNotFound(purchase_id)
        return self.detail(purchase)

    def detail(self, purchase: Purchase) -> PurchaseDetail:
        return PurchaseDetail(purchase, self.suppliers.get(purchase.supplier_id))


class ListPurchases:
    def __init__(self, purchases: PurchaseRepository):
        self.purchases = purchases

    def execute(self, supplier_id: UUID | None = None) -> Sequence[PurchaseSummary]:
        return self.purchases.list(supplier_id=supplier_id)
