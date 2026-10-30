from datetime import date
from unittest import TestCase
from uuid import uuid4

from modules.purchases.application.ports import ProductInfo
from modules.purchases.application.purchase_commands import (
    PRODUCT_INACTIVE,
    PRODUCT_NOT_BUYABLE,
    PRODUCT_MISSING,
    SUPPLIER_NOT_ACTIVE,
    CreatePurchase,
    ItemInput,
    UpdatePurchase,
)
from modules.purchases.domain.exceptions import PurchaseNotEditable, PurchaseNotFound, PurchaseValidationError
from modules.purchases.domain.supplier import Supplier

TODAY = date(2026, 10, 29)


class FakePurchases:
    def __init__(self):
        self.rows = {}
        self.saved = 0

    def get(self, purchase_id, for_update=False):
        return self.rows.get(purchase_id)

    def save(self, purchase):
        self.rows[purchase.id] = purchase
        self.saved += 1
        return purchase


class FakeSuppliers:
    def __init__(self, *suppliers):
        self.rows = {s.id: s for s in suppliers}

    def get(self, supplier_id):
        return self.rows.get(supplier_id)


class FakeProducts:
    def __init__(self, *products):
        self.rows = {p.id: p for p in products}

    def get_products(self, product_ids):
        return {pid: self.rows[pid] for pid in product_ids if pid in self.rows}


def product(name='Harina', active=True, unit='kg', fractions=True, can_buy=True):
    return ProductInfo(id=uuid4(), name=name, active=active, can_buy=can_buy, unit_abbreviation=unit,
                       allows_fractions=fractions)


class PurchaseApplicationCase(TestCase):
    def setUp(self):
        self.supplier = Supplier.create(name='Sur')
        self.purchases = FakePurchases()
        self.flour = product()
        self.suppliers = FakeSuppliers(self.supplier)
        self.products = FakeProducts(self.flour)

    def create_use_case(self):
        return CreatePurchase(self.purchases, self.suppliers, self.products)

    def update_use_case(self):
        return UpdatePurchase(self.purchases, self.suppliers, self.products)

    def create(self, **extra):
        data = {'supplier_id': self.supplier.id, 'purchase_date': TODAY,
                'items': [ItemInput(self.flour.id, '2', '10.00')], **extra}
        return self.create_use_case().execute(**data)


class CreatePurchaseTests(PurchaseApplicationCase):
    def test_creates_with_catalog_snapshot(self):  # AC-01
        purchase = self.create()
        item = purchase.items[0]
        self.assertEqual((item.product_name, item.unit_abbreviation), ('Harina', 'kg'))
        self.assertEqual(self.purchases.saved, 1)

    def test_product_without_unit_has_empty_abbreviation(self):  # EDGE-03
        bare = product(name='Bolsa', unit=None, fractions=False)
        self.products.rows[bare.id] = bare
        purchase = self.create(items=[ItemInput(bare.id, '1.5', '1.00')])
        self.assertEqual(purchase.items[0].unit_abbreviation, '')

    def test_unknown_or_inactive_supplier_is_rejected(self):  # AC-03, INV-01
        inactive = Supplier.create(name='Norte')
        inactive.deactivate()
        self.suppliers.rows[inactive.id] = inactive
        for supplier_id in (uuid4(), inactive.id):
            with self.assertRaises(PurchaseValidationError) as ctx:
                self.create(supplier_id=supplier_id)
            self.assertEqual(ctx.exception.errors['supplier_id'], [SUPPLIER_NOT_ACTIVE])
        self.assertEqual(self.purchases.saved, 0)

    def test_missing_supplier_uses_the_domain_message(self):  # AC-03
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.create(supplier_id=None)
        self.assertEqual(ctx.exception.errors['supplier_id'], ['El proveedor es obligatorio.'])

    def test_missing_and_inactive_products_are_rejected_per_line(self):  # AC-03
        inactive = product(name='Viejo', active=False)
        self.products.rows[inactive.id] = inactive
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.create(items=[ItemInput(self.flour.id, '1', '1'), ItemInput(uuid4(), '1', '1'),
                               ItemInput(inactive.id, '1', '1')])
        lines = ctx.exception.errors['items']
        self.assertEqual(lines[0], {})
        self.assertEqual(lines[1]['product_id'], [PRODUCT_MISSING])
        self.assertEqual(lines[2]['product_id'], [PRODUCT_INACTIVE])

    def test_product_not_enabled_for_purchase_is_rejected_per_line(self):  # AC-19 (PB-CAT-001)
        sellable_only = product(name='Cuñapé', can_buy=False)
        inactive_and_not_buyable = product(name='Viejo', active=False, can_buy=False)
        self.products.rows[sellable_only.id] = sellable_only
        self.products.rows[inactive_and_not_buyable.id] = inactive_and_not_buyable
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.create(items=[ItemInput(self.flour.id, '1', '1'), ItemInput(sellable_only.id, '1', '1'),
                               ItemInput(inactive_and_not_buyable.id, '1', '1')])
        lines = ctx.exception.errors['items']
        self.assertEqual(lines[0], {})
        self.assertEqual(lines[1]['product_id'], [PRODUCT_NOT_BUYABLE])
        self.assertEqual(lines[2]['product_id'], [PRODUCT_INACTIVE])
        self.assertEqual(self.purchases.saved, 0)

    def test_integer_unit_rejects_fractions(self):  # INV-04
        units = product(name='Caja', unit='u', fractions=False)
        self.products.rows[units.id] = units
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.create(items=[ItemInput(units.id, '1.5', '1')])
        self.assertIn('quantity', ctx.exception.errors['items'][0])

    def test_supplier_header_and_line_errors_come_together(self):  # AC-03
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.create(supplier_id=uuid4(), purchase_date=None, items=[ItemInput(self.flour.id, '0', '-1')])
        self.assertEqual(set(ctx.exception.errors), {'supplier_id', 'purchase_date', 'items'})
        self.assertEqual(set(ctx.exception.errors['items'][0]), {'quantity', 'unit_price'})


class UpdatePurchaseTests(PurchaseApplicationCase):
    def test_unknown_purchase(self):  # AC-06
        with self.assertRaises(PurchaseNotFound):
            self.update_use_case().execute(uuid4(), notes='x')

    def test_edits_only_sent_fields(self):  # AC-07
        purchase = self.create(notes='a')
        updated = self.update_use_case().execute(purchase.id, notes='b')
        self.assertEqual((updated.notes, len(updated.items), updated.supplier_id), ('b', 1, self.supplier.id))

    def test_kept_product_may_be_inactive_or_renamed_new_must_be_active(self):  # INV-08, EDGE-04
        purchase = self.create()
        self.products.rows[self.flour.id] = ProductInfo(self.flour.id, 'Harina RENOMBRADA', False, False, 'kg', True)
        updated = self.update_use_case().execute(purchase.id, items=[ItemInput(self.flour.id, '5', '9.00')])
        self.assertEqual((updated.items[0].product_name, str(updated.items[0].quantity)), ('Harina', '5.000'))
        inactive = product(name='Viejo', active=False)
        self.products.rows[inactive.id] = inactive
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.update_use_case().execute(purchase.id, items=[ItemInput(inactive.id, '1', '1')])
        self.assertEqual(ctx.exception.errors['items'][0]['product_id'], [PRODUCT_INACTIVE])

    def test_kept_product_may_stop_being_buyable_but_a_new_one_must_be_buyable(self):  # AC-19, INV-08
        purchase = self.create()
        self.products.rows[self.flour.id] = ProductInfo(self.flour.id, 'Harina', True, False, 'kg', True)
        updated = self.update_use_case().execute(purchase.id, items=[ItemInput(self.flour.id, '5', '9.00')])
        self.assertEqual(updated.items[0].product_name, 'Harina')
        not_buyable = product(name='Cuñapé', can_buy=False)
        self.products.rows[not_buyable.id] = not_buyable
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.update_use_case().execute(purchase.id, items=[ItemInput(not_buyable.id, '1', '1')])
        self.assertEqual(ctx.exception.errors['items'][0]['product_id'], [PRODUCT_NOT_BUYABLE])

    def test_deactivated_supplier_must_be_replaced(self):  # AC-08, EDGE-05
        purchase = self.create()
        self.supplier.deactivate()
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.update_use_case().execute(purchase.id, notes='x')
        self.assertEqual(ctx.exception.errors['supplier_id'], [SUPPLIER_NOT_ACTIVE])
        other = Supplier.create(name='Otro')
        self.suppliers.rows[other.id] = other
        updated = self.update_use_case().execute(purchase.id, supplier_id=other.id)
        self.assertEqual(updated.supplier_id, other.id)

    def test_failed_update_does_not_save(self):  # AC-07
        purchase = self.create()
        saved = self.purchases.saved
        with self.assertRaises(PurchaseValidationError):
            self.update_use_case().execute(purchase.id, notes='x', items=[ItemInput(self.flour.id, '0', '1')])
        self.assertEqual(self.purchases.saved, saved)
        self.assertEqual(self.purchases.rows[purchase.id].notes, '')

    def test_not_editable_purchase(self):  # INV-09
        purchase = self.create()
        purchase.status = object()
        with self.assertRaises(PurchaseNotEditable):
            self.update_use_case().execute(purchase.id, notes='x')
