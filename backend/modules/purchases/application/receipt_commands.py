from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from modules.purchases.domain.enums import InventoryMode
from modules.purchases.domain.exceptions import (
    PurchaseNotFound,
    PurchaseValidationError,
    ReceiptAlreadyReverted,
    ReceiptConflict,
    ReceiptInventoryUnavailable,
    ReceiptNotFound,
    StockShortage,
)
from modules.purchases.domain.purchase import ZERO, Purchase, ReceiptLineDraft
from modules.purchases.domain.receipt import Receipt
from modules.purchases.domain.repositories import PurchaseRepository, ReceiptRepository

from .ports import Actor, ProductCatalog, StockEntry, StockWarehouse

WAREHOUSE_REQUIRED = 'Selecciona un almacén para los productos con control de stock.'
WAREHOUSE_INVALID = 'El almacén no existe o está inactivo.'


@dataclass(frozen=True)
class ReceiptLineInput:
    item_id: UUID
    quantity: object


def suggested_warehouse(warehouses: list[StockWarehouse]) -> UUID | None:
    """El único almacén activo o, si hay varios, el predeterminado."""
    if len(warehouses) == 1:
        return warehouses[0].id
    return next((w.id for w in warehouses if w.is_default), None)


def allows_fractions_by_item(products: ProductCatalog, purchase: Purchase) -> dict[UUID, bool]:
    """Fracciones admitidas por línea de la compra (según la unidad actual del catálogo)."""
    info = products.get_products([item.product_id for item in purchase.items])
    result = {}
    for item in purchase.items:
        product = info.get(item.product_id)
        result[item.id] = True if product is None or product.unit_abbreviation is None else product.allows_fractions
    return result


def received_by_item(receipts: ReceiptRepository, purchase: Purchase) -> dict[UUID, Decimal]:
    totals = receipts.received_totals(purchase.id)
    return {item.id: totals.get(item.id, ZERO) for item in purchase.items}


class RegisterReception:
    """Registra una recepción de una compra confirmada y, con Inventario activo, las entradas de stock.

    Todo ocurre en la transacción del llamador con la compra bloqueada: o se confirma todo o nada.
    Repetir el mismo `receipt_id` devuelve la recepción ya registrada (`created=False`).
    """

    def __init__(self, purchases: PurchaseRepository, receipts: ReceiptRepository, products: ProductCatalog,
                 stock: StockEntry):
        self.purchases = purchases
        self.receipts = receipts
        self.products = products
        self.stock = stock

    def execute(self, purchase_id: UUID, receipt_id: UUID, receipt_date: object, lines: Sequence[ReceiptLineInput],
                warehouse_id: UUID | None, actor: Actor, today: date) -> tuple[Receipt, bool]:
        purchase = self.purchases.get(purchase_id, for_update=True)
        if purchase is None:
            raise PurchaseNotFound(purchase_id)
        existing = self.receipts.get(receipt_id)
        if existing is not None:
            if existing.purchase_id != purchase_id:
                raise ReceiptConflict()
            return existing, False
        fractions = allows_fractions_by_item(self.products, purchase)
        drafts = [ReceiptLineDraft(line.item_id, line.quantity, fractions.get(line.item_id, True))
                  for line in lines]
        receipt = purchase.receive(receipt_id, receipt_date, today, self.receipts.received_totals(purchase_id),
                                   drafts, actor.user_id, actor.user_name)
        self._enter_stock(receipt, warehouse_id, actor)
        saved = self.receipts.save(receipt)
        self.purchases.save(purchase)
        return saved, True

    def _enter_stock(self, receipt: Receipt, warehouse_id: UUID | None, actor: Actor) -> None:
        if not self.stock.is_available():
            receipt.set_inventory_mode(InventoryMode.DOCUMENTAL)
            return
        receipt.set_inventory_mode(InventoryMode.INVENTORY)
        controlled = self.stock.controlled_products([line.product_id for line in receipt.lines])
        entries = [(line.product_id, line.quantity) for line in receipt.lines if line.product_id in controlled]
        if not entries:
            return
        if warehouse_id is None:
            raise PurchaseValidationError({'warehouse_id': [WAREHOUSE_REQUIRED]})
        if all(w.id != warehouse_id for w in self.stock.active_warehouses()):
            raise PurchaseValidationError({'warehouse_id': [WAREHOUSE_INVALID]})
        self.stock.register_entries(warehouse_id, entries, receipt.id, receipt.reference, actor)
        receipt.assign_warehouse(warehouse_id)


@dataclass(frozen=True)
class ShortageLine:
    product_id: UUID
    product_name: str
    unit_abbreviation: str
    requested: Decimal
    available: Decimal


class RevertStockShortage(Exception):
    """Revertir la recepción dejaría stock negativo bloqueado; lista todas las líneas sin saldo, ya nombradas."""

    def __init__(self, warehouse_id: UUID, warehouse_name: str, lines: list[ShortageLine]):
        super().__init__('No hay saldo suficiente para revertir la recepción.')
        self.warehouse_id = warehouse_id
        self.warehouse_name = warehouse_name
        self.lines = lines


class RevertReception:
    """Revierte una recepción completa: sus entradas de stock (todas o ninguna) y el estado de la compra.

    Con la compra bloqueada y en la transacción del llamador: o se revierte todo o nada. No toca los pagos.
    """

    def __init__(self, purchases: PurchaseRepository, receipts: ReceiptRepository, stock: StockEntry):
        self.purchases = purchases
        self.receipts = receipts
        self.stock = stock

    def execute(self, purchase_id: UUID, receipt_id: UUID, reason: object, actor: Actor, now: datetime) -> Receipt:
        purchase = self.purchases.get(purchase_id, for_update=True)
        if purchase is None:
            raise PurchaseNotFound(purchase_id)
        receipt = self.receipts.get(receipt_id)
        if receipt is None or receipt.purchase_id != purchase_id:
            raise ReceiptNotFound(receipt_id)
        receipt.revert(reason, actor.user_id, actor.user_name, now)  # valida estado y motivo antes de tocar stock
        if receipt.moved_stock:
            if not self.stock.is_available():
                raise ReceiptInventoryUnavailable()
            try:
                self.stock.reverse_entries(receipt.id, receipt.revert_reason, actor)
            except StockShortage as exc:
                raise self._shortage(receipt, exc) from exc
        self.receipts.mark_reverted(receipt)
        purchase.recompute_reception(self.receipts.received_totals(purchase_id))
        self.purchases.save(purchase)
        return receipt

    def _shortage(self, receipt: Receipt, exc: StockShortage) -> RevertStockShortage:
        names = {line.product_id: (line.product_name, line.unit_abbreviation) for line in receipt.lines}
        lines = [ShortageLine(pid, *names.get(pid, ('', '')), requested, available)
                 for pid, requested, available in exc.shortages]
        warehouse = next((m.warehouse_name for m in self.stock.movements_for(receipt.id)
                          if m.warehouse_id == exc.warehouse_id), '')
        return RevertStockShortage(exc.warehouse_id, warehouse, lines)
