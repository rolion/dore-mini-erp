from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from modules.purchases.domain.enums import InventoryMode, PurchaseStatus
from modules.purchases.domain.exceptions import PurchaseNotFound, PurchaseNotReceivable, ReceiptNotFound
from modules.purchases.domain.purchase import Purchase
from modules.purchases.domain.receipt import Receipt
from modules.purchases.domain.repositories import PurchaseRepository, ReceiptRepository

from .ports import ProductCatalog, StockEntry, StockEntryMovement, StockWarehouse
from .receipt_commands import allows_fractions_by_item, received_by_item, suggested_warehouse


@dataclass(frozen=True)
class ReceptionFormLine:
    item_id: UUID
    product_id: UUID
    product_name: str
    unit_abbreviation: str
    allows_fractions: bool
    tracks_stock: bool
    ordered: Decimal
    received: Decimal
    pending: Decimal


@dataclass(frozen=True)
class ReceptionForm:
    inventory_enabled: bool
    warehouses: list[StockWarehouse]
    warehouse_id: UUID | None
    lines: list[ReceptionFormLine]


@dataclass(frozen=True)
class ReceiptDetail:
    receipt: Receipt
    purchase: Purchase
    warehouse_name: str
    # Según el modo guardado al confirmar: None si fue documental (o modo desconocido sin Inventario hoy).
    movements: list[StockEntryMovement] | None
    inventory_available: bool  # estado actual del módulo (solo para decidir enlaces)


def _purchase(purchases: PurchaseRepository, purchase_id: UUID) -> Purchase:
    purchase = purchases.get(purchase_id)
    if purchase is None:
        raise PurchaseNotFound(purchase_id)
    return purchase


class GetReceptionForm:
    """Lo que necesita el formulario de recepción: pendientes por línea y datos de Inventario. Informativo."""

    def __init__(self, purchases: PurchaseRepository, receipts: ReceiptRepository, products: ProductCatalog,
                 stock: StockEntry):
        self.purchases = purchases
        self.receipts = receipts
        self.products = products
        self.stock = stock

    def execute(self, purchase_id: UUID) -> ReceptionForm:
        purchase = _purchase(self.purchases, purchase_id)
        if purchase.status is not PurchaseStatus.CONFIRMED:
            raise PurchaseNotReceivable()
        received = received_by_item(self.receipts, purchase)
        fractions = allows_fractions_by_item(self.products, purchase)
        enabled = self.stock.is_available()
        controlled = self.stock.controlled_products([i.product_id for i in purchase.items]) if enabled else {}
        lines = [ReceptionFormLine(
            item_id=i.id, product_id=i.product_id, product_name=i.product_name,
            unit_abbreviation=i.unit_abbreviation, allows_fractions=fractions[i.id],
            tracks_stock=i.product_id in controlled, ordered=i.quantity, received=received[i.id],
            pending=max(i.quantity - received[i.id], Decimal('0'))) for i in purchase.items]
        needs_warehouse = any(line.tracks_stock and line.pending > 0 for line in lines)
        warehouses = self.stock.active_warehouses() if needs_warehouse else []
        return ReceptionForm(enabled, warehouses, suggested_warehouse(warehouses) if warehouses else None, lines)


class ListReceipts:
    def __init__(self, purchases: PurchaseRepository, receipts: ReceiptRepository):
        self.purchases = purchases
        self.receipts = receipts

    def execute(self, purchase_id: UUID) -> list[Receipt]:
        _purchase(self.purchases, purchase_id)
        return list(self.receipts.list_for_purchase(purchase_id))


class GetReceipt:
    def __init__(self, purchases: PurchaseRepository, receipts: ReceiptRepository, stock: StockEntry):
        self.purchases = purchases
        self.receipts = receipts
        self.stock = stock

    def execute(self, purchase_id: UUID, receipt_id: UUID) -> ReceiptDetail:
        purchase = _purchase(self.purchases, purchase_id)
        receipt = self.receipts.get(receipt_id)
        if receipt is None or receipt.purchase_id != purchase_id:
            raise ReceiptNotFound(receipt_id)
        return self.detail(purchase, receipt)

    def detail(self, purchase: Purchase, receipt: Receipt) -> ReceiptDetail:
        available = self.stock.is_available()
        mode = receipt.inventory_mode
        if mode is None:  # recepción anterior al modo guardado y sin almacén: comportamiento previo
            reads_ledger = available
        else:
            reads_ledger = mode is InventoryMode.INVENTORY
        movements = self.stock.movements_for(receipt.id) if reads_ledger else None
        name = ''
        if receipt.warehouse_id is not None and reads_ledger:
            name = next((m.warehouse_name for m in movements or [] if m.warehouse_id == receipt.warehouse_id), '')
            if not name and available:
                name = next((w.name for w in self.stock.active_warehouses() if w.id == receipt.warehouse_id), '')
        return ReceiptDetail(receipt, purchase, name, movements, available)
