from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

import importlib

from django.apps import apps

from modules.purchases.domain.enums import InventoryMode, ReceiptStatus
from modules.purchases.domain.exceptions import ReceiptConflict
from modules.purchases.domain.purchase import ItemDraft, Purchase, ReceiptLineDraft
from modules.purchases.infrastructure.django.models import ReceiptModel, SupplierModel
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository
from modules.purchases.infrastructure.django.receipt_repository import DjangoReceiptRepository

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 30)


class ReceiptRepositoryTests(TestCase):
    def setUp(self):
        self.company_id = uuid4()
        self.purchases = DjangoPurchaseRepository(self.company_id)
        self.receipts = DjangoReceiptRepository(self.company_id)
        supplier = SupplierModel.objects.create(company_id=self.company_id, name='Sur')
        purchase = Purchase.create(supplier_id=supplier.id, purchase_date=TODAY, items=[
            ItemDraft(uuid4(), '10', '5.00', product_name='Harina', unit_abbreviation='kg'),
            ItemDraft(uuid4(), '4', '2.00', product_name='Bolsa', unit_abbreviation='u')])
        purchase.confirm(NOW)
        self.purchase = self.purchases.save(purchase)

    def receive(self, quantities, warehouse_id=None):
        drafts = [ReceiptLineDraft(item.id, q) for item, q in zip(self.purchase.items, quantities) if q]
        receipt = self.purchase.receive(uuid4(), TODAY, TODAY, self.receipts.received_totals(self.purchase.id),
                                        drafts, uuid4(), 'Ana')
        receipt.assign_warehouse(warehouse_id)
        return self.receipts.save(receipt)

    def test_round_trip(self):  # AC-13
        warehouse_id = uuid4()
        saved = self.receive(['4', None], warehouse_id)
        loaded = self.receipts.get(saved.id)
        self.assertEqual((loaded.purchase_id, loaded.receipt_date, loaded.user_name, loaded.warehouse_id,
                          loaded.status), (self.purchase.id, TODAY, 'Ana', warehouse_id, ReceiptStatus.CONFIRMED))
        self.assertEqual([(l.product_name, l.unit_abbreviation, l.quantity) for l in loaded.lines],
                         [('Harina', 'kg', Decimal('4.000'))])
        self.assertIsNotNone(saved.created_at)

    def test_inventory_mode_round_trip(self):  # INV-01
        for mode in (InventoryMode.INVENTORY, InventoryMode.DOCUMENTAL, None):
            receipt = self.purchase.receive(uuid4(), TODAY, TODAY, {}, [ReceiptLineDraft(self.purchase.items[0].id, '1')],
                                            None, 'Ana')
            receipt.inventory_mode = mode
            self.assertEqual(self.receipts.get(self.receipts.save(receipt).id).inventory_mode, mode)

    def test_migration_backfills_only_receipts_with_a_warehouse(self):  # AC-07, INV-04
        with_warehouse = self.receive(['1', None], uuid4())
        without = self.receive(['1', None])
        ReceiptModel.objects.update(inventory_mode=None)
        migration = importlib.import_module('modules.purchases.migrations.0005_receipt_inventory_mode')
        migration.backfill_inventory_mode(apps, None)
        self.assertEqual(self.receipts.get(with_warehouse.id).inventory_mode, InventoryMode.INVENTORY)
        self.assertIsNone(self.receipts.get(without.id).inventory_mode)

    def test_received_totals_add_confirmed_receipts_per_line(self):  # INV-02
        self.receive(['4', '1'])
        self.receive(['2', None])
        first, second = self.purchase.items
        self.assertEqual(self.receipts.received_totals(self.purchase.id),
                         {first.id: Decimal('6.000'), second.id: Decimal('1.000')})

    def test_reverted_receipts_do_not_count(self):  # H-03
        saved = self.receive(['4', None])
        ReceiptModel.objects.filter(pk=saved.id).update(status='reverted')
        self.assertEqual(self.receipts.received_totals(self.purchase.id), {})

    def test_company_isolation(self):  # INV-07
        saved = self.receive(['4', None])
        other = DjangoReceiptRepository(uuid4())
        self.assertIsNone(other.get(saved.id))
        self.assertEqual((other.list_for_purchase(self.purchase.id), other.received_totals(self.purchase.id)), ([], {}))

    def test_list_is_newest_first(self):
        first = self.receive(['1', None])
        second = self.receive(['1', None])
        self.assertEqual({r.id for r in self.receipts.list_for_purchase(self.purchase.id)}, {first.id, second.id})

    def test_line_ids_survive_saving_the_purchase_again(self):  # riesgo: referencia por UUID sin FK
        before = [i.id for i in self.purchase.items]
        self.receive(['4', None])
        self.purchases.save(self.purchases.get(self.purchase.id))
        self.assertEqual([i.id for i in self.purchases.get(self.purchase.id).items], before)
        self.assertEqual(self.receipts.received_totals(self.purchase.id), {before[0]: Decimal('4.000')})

    def test_reusing_an_id_from_another_company_conflicts(self):  # AC-11
        saved = self.receive(['4', None])
        stranger = DjangoReceiptRepository(uuid4())
        with self.assertRaises(ReceiptConflict):
            stranger.save(saved)
