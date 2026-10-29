from datetime import date
from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from modules.purchases.domain.exceptions import PurchaseNotEditable, PurchaseValidationError
from modules.purchases.domain.purchase import (
    MAX_ITEMS,
    UNSET,
    ItemDraft,
    Purchase,
    PurchaseItem,
    compute_subtotal,
)

SUPPLIER = uuid4()
TODAY = date(2026, 10, 29)


def draft(quantity='1', unit_price='10.00', product_id=None, **extra):
    return ItemDraft(product_id=product_id or uuid4(), quantity=quantity, unit_price=unit_price,
                     product_name=extra.pop('product_name', 'Harina'), **extra)


def make(items=None, **extra):
    return Purchase.create(supplier_id=extra.pop('supplier_id', SUPPLIER), purchase_date=extra.pop('purchase_date', TODAY),
                           items=items, **extra)


class CreatePurchaseTests(TestCase):
    def test_header_is_normalized_and_status_is_draft(self):  # AC-01, AC-02, INV-03
        purchase = make(external_reference='  F-1  ', notes=None)
        self.assertEqual((purchase.external_reference, purchase.notes), ('F-1', ''))
        self.assertEqual(purchase.status.value, 'draft')
        self.assertTrue(purchase.editable)
        self.assertEqual((purchase.items, purchase.total), ([], Decimal('0.00')))

    def test_total_is_the_sum_of_subtotals(self):  # AC-01, INV-06
        purchase = make([draft('2', '10.50'), draft('0.5', '3.00')])
        self.assertEqual([i.subtotal for i in purchase.items], [Decimal('21.00'), Decimal('1.50')])
        self.assertEqual(purchase.total, Decimal('22.50'))

    def test_rounding_is_half_up_to_two_decimals(self):  # EDGE-01
        self.assertEqual(compute_subtotal(Decimal('0.333'), Decimal('10.00')), Decimal('3.33'))
        self.assertEqual(compute_subtotal(Decimal('1.005'), Decimal('1.00')), Decimal('1.01'))
        self.assertEqual(compute_subtotal(Decimal('0.001'), Decimal('0.01')), Decimal('0.00'))

    def test_zero_price_is_allowed(self):  # INV-04
        self.assertEqual(make([draft('3', '0')]).total, Decimal('0.00'))

    def test_header_errors_are_reported_together(self):  # AC-03, INV-01..03
        with self.assertRaises(PurchaseValidationError) as ctx:
            Purchase.create(supplier_id=None, purchase_date=None, external_reference='x' * 101, notes='n' * 2001)
        self.assertEqual(set(ctx.exception.errors), {'supplier_id', 'purchase_date', 'external_reference', 'notes'})

    def test_purchase_date_must_be_a_date(self):  # INV-02
        for value in ('2026-10-29', 5):
            with self.assertRaises(PurchaseValidationError) as ctx:
                make(purchase_date=value)
            self.assertIn('purchase_date', ctx.exception.errors)

    def test_invalid_quantities_are_reported_per_line(self):  # AC-03, AC-04, INV-04
        cases = ['0', '-1', '1.0005', '100000000', 'abc', '1e3', 'NaN', True, 1.5, None]
        for quantity in cases:
            with self.assertRaises(PurchaseValidationError, msg=repr(quantity)) as ctx:
                make([draft(), draft(quantity=quantity)])
            lines = ctx.exception.errors['items']
            self.assertEqual(lines[0], {})
            self.assertIn('quantity', lines[1], repr(quantity))

    def test_invalid_prices_are_reported_per_line(self):  # AC-03, AC-04, INV-04
        for price in ('-0.01', '1.001', '10000000000.00', 'x', 2.5, None, False):
            with self.assertRaises(PurchaseValidationError, msg=repr(price)) as ctx:
                make([draft(unit_price=price)])
            self.assertIn('unit_price', ctx.exception.errors['items'][0], repr(price))

    def test_huge_numbers_are_a_line_error_not_a_crash(self):  # AC-03, AC-04, EDGE-06 (REV-02)
        for quantity, price in (('1' * 40, '1'), (10 ** 40, '1'), ('1', '1' * 40), ('1', 10 ** 40)):
            with self.assertRaises(PurchaseValidationError, msg=repr((quantity, price))) as ctx:
                make([draft(quantity=quantity, unit_price=price)])
            self.assertTrue({'quantity', 'unit_price'} & set(ctx.exception.errors['items'][0]))

    def test_fractions_rejected_when_the_unit_does_not_allow_them(self):  # INV-04
        with self.assertRaises(PurchaseValidationError) as ctx:
            make([draft('1.5', allows_fractions=False)])
        self.assertIn('quantity', ctx.exception.errors['items'][0])
        self.assertEqual(make([draft('2.000', allows_fractions=False)]).items[0].quantity, Decimal('2.000'))

    def test_fractions_allowed_up_to_three_decimals(self):  # EDGE-03
        self.assertEqual(make([draft('0.001')]).items[0].quantity, Decimal('0.001'))

    def test_duplicate_product_marks_the_second_line(self):  # INV-05, EDGE-08
        product = uuid4()
        with self.assertRaises(PurchaseValidationError) as ctx:
            make([draft(product_id=product), draft(product_id=product)])
        lines = ctx.exception.errors['items']
        self.assertEqual(lines[0], {})
        self.assertIn('product_id', lines[1])

    def test_product_error_from_the_application_marks_the_line(self):  # AC-03
        with self.assertRaises(PurchaseValidationError) as ctx:
            make([draft(product_error='El producto está inactivo.')])
        self.assertEqual(ctx.exception.errors['items'][0]['product_id'], ['El producto está inactivo.'])

    def test_at_most_200_lines(self):  # INV-05
        make([draft() for _ in range(MAX_ITEMS)])
        with self.assertRaises(PurchaseValidationError) as ctx:
            make([draft() for _ in range(MAX_ITEMS + 1)])
        self.assertIn('items', ctx.exception.errors)

    def test_amount_over_the_maximum_is_an_error_of_the_line(self):  # EDGE-02
        with self.assertRaises(PurchaseValidationError) as ctx:
            make([draft('99999999', '9999999999.99')])
        self.assertIn('quantity', ctx.exception.errors['items'][0])

    def test_header_and_line_errors_come_together(self):  # AC-03
        with self.assertRaises(PurchaseValidationError) as ctx:
            Purchase.create(supplier_id=None, purchase_date=TODAY, items=[draft('0')])
        self.assertEqual(set(ctx.exception.errors), {'supplier_id', 'items'})

    def test_no_tax_or_discount_exist(self):  # INV-07
        purchase = make([draft('1', '10')])
        for name in ('discount', 'tax', 'taxes', 'extra_costs'):
            self.assertFalse(hasattr(purchase, name))


class UpdatePurchaseTests(TestCase):
    def test_only_sent_fields_change(self):  # AC-07
        purchase = make([draft()], external_reference='A', notes='n')
        items = list(purchase.items)
        purchase.update(notes='nuevo')
        self.assertEqual((purchase.external_reference, purchase.notes, purchase.items), ('A', 'nuevo', items))

    def test_none_clears_optional_text(self):  # AC-07
        purchase = make(external_reference='A', notes='n')
        purchase.update(external_reference=None, notes='')
        self.assertEqual((purchase.external_reference, purchase.notes), ('', ''))

    def test_items_replace_the_whole_set(self):  # AC-07
        first, second = uuid4(), uuid4()
        purchase = make([draft(product_id=first)])
        purchase.update(items=[draft('3', '2', product_id=second)])
        self.assertEqual([i.product_id for i in purchase.items], [second])
        purchase.update(items=[])
        self.assertEqual(purchase.items, [])

    def test_existing_product_keeps_its_snapshot_new_gets_current(self):  # INV-08, EDGE-04
        kept, added = uuid4(), uuid4()
        purchase = make([draft(product_id=kept, product_name='Harina 1kg', unit_abbreviation='kg')])
        purchase.update(items=[
            draft('5', '9.00', product_id=kept, product_name='Harina RENOMBRADA', unit_abbreviation='lb'),
            draft('1', '1.00', product_id=added, product_name='Azúcar', unit_abbreviation='kg'),
        ])
        self.assertEqual([(i.product_name, i.unit_abbreviation) for i in purchase.items],
                         [('Harina 1kg', 'kg'), ('Azúcar', 'kg')])
        self.assertEqual(purchase.items[0].quantity, Decimal('5.000'))
        self.assertEqual(purchase.items[0].unit_price, Decimal('9.00'))

    def test_failed_update_changes_nothing(self):  # AC-07
        purchase = make([draft()], notes='n')
        before = (purchase.supplier_id, purchase.notes, list(purchase.items))
        with self.assertRaises(PurchaseValidationError):
            purchase.update(notes='cambiada', items=[draft('0')])
        self.assertEqual((purchase.supplier_id, purchase.notes, purchase.items), before)

    def test_supplier_cannot_be_cleared(self):  # INV-01
        purchase = make()
        with self.assertRaises(PurchaseValidationError) as ctx:
            purchase.update(supplier_id=None)
        self.assertIn('supplier_id', ctx.exception.errors)

    def test_unset_marker_means_not_sent(self):
        purchase = make([draft()])
        purchase.update(supplier_id=UNSET, items=UNSET)
        self.assertEqual(len(purchase.items), 1)

    def test_only_a_draft_is_editable(self):  # INV-09
        purchase = make()
        purchase.status = object()  # un estado futuro distinto de borrador
        with self.assertRaises(PurchaseNotEditable):
            purchase.update(notes='x')

    def test_derived_amounts_are_not_assignable(self):  # INV-06
        purchase = make([draft()])
        with self.assertRaises(AttributeError):
            purchase.total = Decimal('1')
        with self.assertRaises(AttributeError):
            purchase.items[0].subtotal = Decimal('1')
        self.assertIsInstance(purchase.items[0], PurchaseItem)
