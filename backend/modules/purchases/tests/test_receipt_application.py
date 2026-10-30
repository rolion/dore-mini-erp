from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from modules.purchases.application.ports import Actor, StockEntryMovement, StockProductInfo, StockWarehouse
from modules.purchases.application.receipt_commands import (
    WAREHOUSE_INVALID,
    WAREHOUSE_REQUIRED,
    ReceiptLineInput,
    RegisterReception,
)
from modules.purchases.application.receipt_queries import GetReceipt, GetReceptionForm, ListReceipts
from modules.purchases.domain.enums import InventoryMode, ReceptionStatus
from modules.purchases.domain.exceptions import (
    PurchaseNotFound,
    PurchaseNotReceivable,
    PurchaseValidationError,
    ReceiptConflict,
    ReceiptNotFound,
)
from modules.purchases.tests.test_purchase_application import PurchaseApplicationCase, product

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 30)
ACTOR = Actor(uuid4(), 'Ana')


class FakeReceipts:
    def __init__(self):
        self.rows = {}

    def get(self, receipt_id):
        return self.rows.get(receipt_id)

    def save(self, receipt):
        self.rows[receipt.id] = receipt
        return receipt

    def list_for_purchase(self, purchase_id):
        return [r for r in self.rows.values() if r.purchase_id == purchase_id]

    def received_totals(self, purchase_id):
        totals = {}
        for receipt in self.list_for_purchase(purchase_id):
            for line in receipt.lines:
                totals[line.purchase_item_id] = totals.get(line.purchase_item_id, Decimal('0')) + line.quantity
        return totals


class FakeStock:
    def __init__(self, enabled=True, controlled=(), warehouses=(), fail=False):
        self.enabled = enabled
        self.controlled = {pid: StockProductInfo(pid, 'P', 'kg') for pid in controlled}
        self.warehouses = list(warehouses)
        self.fail = fail
        self.entries = []

    def is_available(self):
        return self.enabled

    def controlled_products(self, product_ids):
        return {pid: self.controlled[pid] for pid in product_ids if pid in self.controlled}

    def active_warehouses(self):
        return self.warehouses

    def register_entries(self, warehouse_id, lines, receipt_id, reference, actor):
        if self.fail:
            raise PurchaseValidationError({'warehouse_id': ['El almacén está inactivo.']})
        self.entries.append((warehouse_id, lines, receipt_id, reference, actor))

    def movements_for(self, receipt_id):
        return [StockEntryMovement(uuid4(), pid, 'P', 'kg', wid, 'Central', qty)
                for wid, lines, rid, _, _ in self.entries if rid == receipt_id for pid, qty in lines]


class ReceptionCase(PurchaseApplicationCase):
    def setUp(self):
        super().setUp()
        self.receipts = FakeReceipts()
        self.warehouse = StockWarehouse(uuid4(), 'Central', True)
        self.stock = FakeStock(enabled=False)
        self.purchase = self.create(items=[
            self.item(self.flour, '10'), ])
        from modules.purchases.application.purchase_commands import ConfirmPurchase
        ConfirmPurchase(self.purchases, self.suppliers).execute(self.purchase.id, NOW)
        self.item_id = self.purchase.items[0].id

    def item(self, info, quantity):
        from modules.purchases.application.purchase_commands import ItemInput
        return ItemInput(info.id, quantity, '5.00')

    def register(self, quantity='4', receipt_id=None, warehouse_id=None, lines=None, purchase_id=None,
                 receipt_date=TODAY):
        use_case = RegisterReception(self.purchases, self.receipts, self.products, self.stock)
        return use_case.execute(
            purchase_id or self.purchase.id, receipt_id or uuid4(), receipt_date,
            lines if lines is not None else [ReceiptLineInput(self.item_id, quantity)], warehouse_id, ACTOR, TODAY)

    def with_inventory(self, warehouses=None, controlled=True):
        warehouses = [self.warehouse] if warehouses is None else warehouses
        self.stock = FakeStock(True, [self.flour.id] if controlled else [], warehouses)


class RegisterReceptionTests(ReceptionCase):
    def test_documentary_reception_without_inventory(self):  # AC-07, INV-09
        receipt, created = self.register('4', warehouse_id=uuid4())
        self.assertTrue(created)
        self.assertEqual((receipt.warehouse_id, self.stock.entries), (None, []))
        self.assertEqual(receipt.inventory_mode, InventoryMode.DOCUMENTAL)  # INV-01
        self.assertEqual(self.purchases.rows[self.purchase.id].reception_status, ReceptionStatus.PARTIAL)
        self.assertEqual((receipt.user_name, receipt.receipt_date), ('Ana', TODAY))

    def test_accumulates_until_complete(self):  # AC-02
        self.register('4')
        self.register('6')
        self.assertEqual(self.purchases.rows[self.purchase.id].reception_status, ReceptionStatus.RECEIVED)
        with self.assertRaises(PurchaseValidationError):
            self.register('1')

    def test_cannot_exceed_across_receptions(self):  # AC-03, INV-02
        self.register('8')
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.register('3')
        self.assertIn('pendiente', ctx.exception.errors['lines'][0]['quantity'][0])
        self.assertEqual(len(self.receipts.rows), 1)

    def test_fraction_not_allowed_by_the_catalog_unit(self):  # EDGE-06
        self.products.rows[self.flour.id] = product('Harina', unit='u', fractions=False)
        self.products.rows[self.flour.id] = type(self.flour)(
            id=self.flour.id, name='Harina', active=True, can_buy=True, unit_abbreviation='u', allows_fractions=False)
        with self.assertRaises(PurchaseValidationError):
            self.register('1.5')

    def test_unknown_or_unconfirmed_purchase(self):  # AC-06
        with self.assertRaises(PurchaseNotFound):
            self.register(purchase_id=uuid4())
        other = self.create()
        with self.assertRaises(PurchaseNotReceivable):
            self.register(purchase_id=other.id, lines=[ReceiptLineInput(other.items[0].id, '1')])

    def test_controlled_lines_enter_stock_in_the_chosen_warehouse(self):  # AC-08, INV-08
        self.with_inventory()
        receipt, _ = self.register('4', warehouse_id=self.warehouse.id)
        warehouse_id, lines, receipt_id, reference, actor = self.stock.entries[0]
        self.assertEqual((warehouse_id, lines, receipt_id, reference, actor),
                         (self.warehouse.id, [(self.flour.id, Decimal('4.000'))], receipt.id, receipt.reference, ACTOR))
        self.assertEqual(receipt.warehouse_id, self.warehouse.id)

    def test_warehouse_is_required_and_must_be_active(self):  # AC-08
        self.with_inventory()
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.register('4')
        self.assertEqual(ctx.exception.errors, {'warehouse_id': [WAREHOUSE_REQUIRED]})
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.register('4', warehouse_id=uuid4())
        self.assertEqual(ctx.exception.errors, {'warehouse_id': [WAREHOUSE_INVALID]})
        self.assertEqual((self.receipts.rows, self.stock.entries), ({}, []))

    def test_uncontrolled_products_need_no_warehouse(self):  # AC-09, EDGE-03
        self.with_inventory(controlled=False)
        receipt, _ = self.register('4')
        self.assertEqual((receipt.warehouse_id, self.stock.entries), (None, []))

    def test_stock_failure_leaves_nothing_saved(self):  # AC-10
        self.with_inventory()
        self.stock.fail = True
        saved = self.purchases.saved
        with self.assertRaises(PurchaseValidationError):
            self.register('4', warehouse_id=self.warehouse.id)
        self.assertEqual(self.receipts.rows, {})
        self.assertEqual(self.purchases.saved, saved)  # la compra no se guarda (en BD la transacción revierte)

    def test_repeating_a_receipt_id_returns_the_same_one(self):  # AC-11, INV-10
        self.with_inventory()
        rid = uuid4()
        first, created = self.register('4', receipt_id=rid, warehouse_id=self.warehouse.id)
        again, created_again = self.register('4', receipt_id=rid, warehouse_id=self.warehouse.id)
        self.assertEqual((created, created_again, again.id), (True, False, first.id))
        self.assertEqual((len(self.receipts.rows), len(self.stock.entries)), (1, 1))

    def test_a_receipt_id_of_another_purchase_conflicts(self):  # AC-11
        rid = uuid4()
        self.register('4', receipt_id=rid)
        other = self.create()
        from modules.purchases.application.purchase_commands import ConfirmPurchase
        ConfirmPurchase(self.purchases, self.suppliers).execute(other.id, NOW)
        with self.assertRaises(ReceiptConflict):
            self.register(receipt_id=rid, purchase_id=other.id, lines=[ReceiptLineInput(other.items[0].id, '1')])


class ReceptionQueriesTests(ReceptionCase):
    def form(self):
        return GetReceptionForm(self.purchases, self.receipts, self.products, self.stock).execute(self.purchase.id)

    def test_form_lines_show_pending_and_hide_inventory_when_off(self):  # AC-14
        self.register('4')
        form = self.form()
        line = form.lines[0]
        self.assertEqual((form.inventory_enabled, form.warehouses, form.warehouse_id), (False, [], None))
        self.assertEqual((line.ordered, line.received, line.pending, line.tracks_stock),
                         (Decimal('10.000'), Decimal('4.000'), Decimal('6.000'), False))

    def test_form_suggests_the_only_or_default_warehouse(self):  # AC-14
        self.with_inventory()
        form = self.form()
        self.assertEqual((form.inventory_enabled, form.warehouse_id, form.lines[0].tracks_stock),
                         (True, self.warehouse.id, True))
        second = StockWarehouse(uuid4(), 'Norte', False)
        self.with_inventory([second, self.warehouse])
        self.assertEqual(self.form().warehouse_id, self.warehouse.id)

    def test_form_has_no_warehouses_when_nothing_controlled_is_pending(self):  # AC-14
        self.with_inventory(controlled=False)
        self.assertEqual(self.form().warehouses, [])
        self.with_inventory()
        self.register('10', warehouse_id=self.warehouse.id)
        self.assertEqual((self.form().warehouses, self.form().lines[0].pending), ([], Decimal('0')))

    def test_form_only_for_confirmed_purchases(self):  # AC-14
        draft_purchase = self.create()
        with self.assertRaises(PurchaseNotReceivable):
            GetReceptionForm(self.purchases, self.receipts, self.products, self.stock).execute(draft_purchase.id)

    def test_list_and_detail(self):  # AC-13
        self.with_inventory()
        receipt, _ = self.register('4', warehouse_id=self.warehouse.id)
        self.assertEqual([r.id for r in ListReceipts(self.purchases, self.receipts).execute(self.purchase.id)],
                         [receipt.id])
        detail = GetReceipt(self.purchases, self.receipts, self.stock).execute(self.purchase.id, receipt.id)
        self.assertEqual((detail.warehouse_name, len(detail.movements)), ('Central', 1))
        self.assertTrue(detail.inventory_available)

    def detail(self, receipt):
        return GetReceipt(self.purchases, self.receipts, self.stock).execute(self.purchase.id, receipt.id)

    def test_detail_keeps_the_mode_when_inventory_is_turned_off_later(self):  # AC-04, INV-02, INV-03
        self.with_inventory()
        receipt, _ = self.register('4', warehouse_id=self.warehouse.id)
        self.stock.enabled = False
        detail = self.detail(receipt)
        self.assertEqual((detail.receipt.inventory_mode, detail.inventory_available), (InventoryMode.INVENTORY, False))
        self.assertEqual((detail.warehouse_name, len(detail.movements)), ('Central', 1))

    def test_documentary_detail_never_shows_movements_when_inventory_is_turned_on_later(self):  # AC-05, EDGE-02
        receipt, _ = self.register('4')
        self.with_inventory()
        detail = self.detail(receipt)
        self.assertEqual((detail.receipt.inventory_mode, detail.movements, detail.warehouse_name),
                         (InventoryMode.DOCUMENTAL, None, ''))

    def test_stock_entry_is_known_only_in_inventory_mode(self):  # AC-06
        self.with_inventory()
        receipt, _ = self.register('4', warehouse_id=self.warehouse.id)
        detail = self.detail(receipt)
        self.assertEqual((detail.stock_entry(self.flour.id), detail.stock_entry(uuid4())), (True, False))
        self.stock.enabled = False
        self.assertEqual(self.detail(receipt).stock_entry(self.flour.id), True)  # sigue leyendo el libro
        documentary, _ = self.register('1')
        self.assertIsNone(self.detail(documentary).stock_entry(self.flour.id))

    def test_unknown_mode_keeps_the_previous_behaviour(self):  # AC-07, EDGE-03
        receipt, _ = self.register('4')
        self.receipts.rows[receipt.id].inventory_mode = None
        self.assertIsNone(self.detail(receipt).movements)
        self.with_inventory()
        self.assertEqual(self.detail(receipt).movements, [])

    def test_inventory_mode_without_controlled_lines_has_empty_movements(self):  # AC-03
        self.with_inventory(controlled=False)
        receipt, _ = self.register('4')
        self.assertEqual(receipt.inventory_mode, InventoryMode.INVENTORY)
        self.assertEqual(self.detail(receipt).movements, [])

    def test_retry_after_inventory_changes_returns_the_original_receipt(self):  # AC-09, INV-05
        self.with_inventory()
        rid = uuid4()
        first, _ = self.register('4', receipt_id=rid, warehouse_id=self.warehouse.id)
        self.stock.enabled = False
        again, created = self.register('4', receipt_id=rid, warehouse_id=self.warehouse.id)
        self.assertEqual((created, again.inventory_mode, len(self.stock.entries)), (False, InventoryMode.INVENTORY, 1))

    def test_receipt_of_another_purchase_is_not_found(self):  # AC-13
        receipt, _ = self.register('4')
        other = self.create()
        with self.assertRaises(ReceiptNotFound):
            GetReceipt(self.purchases, self.receipts, self.stock).execute(other.id, receipt.id)
        with self.assertRaises(PurchaseNotFound):
            ListReceipts(self.purchases, self.receipts).execute(uuid4())
