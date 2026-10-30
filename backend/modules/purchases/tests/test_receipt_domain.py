from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from modules.purchases.domain.enums import InventoryMode, PaymentStatus, ReceiptStatus, ReceptionStatus
from modules.purchases.domain.exceptions import (
    PurchaseNotReceivable,
    PurchaseValidationError,
    ReceiptInventoryModeAlreadySet,
)
from modules.purchases.domain.purchase import ReceiptLineDraft
from modules.purchases.tests.test_purchase_domain import draft, make

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 30)
USER = uuid4()


def confirmed(*quantities):
    purchase = make([draft(q, '10.00') for q in quantities])
    purchase.confirm(NOW)
    return purchase


def receive(purchase, lines, before=None, receipt_date=TODAY):
    drafts = [ReceiptLineDraft(item_id, quantity) for item_id, quantity in lines]
    return purchase.receive(uuid4(), receipt_date, TODAY, before or {}, drafts, USER, 'Ana')


class InventoryModeTests(TestCase):
    def test_a_new_receipt_has_no_mode_until_it_is_set(self):  # INV-01
        purchase = confirmed('3')
        receipt = receive(purchase, [(purchase.items[0].id, '3')])
        self.assertIsNone(receipt.inventory_mode)
        receipt.set_inventory_mode(InventoryMode.INVENTORY)
        self.assertEqual(receipt.inventory_mode, InventoryMode.INVENTORY)

    def test_the_mode_cannot_change_once_set(self):  # INV-01, INV-02
        purchase = confirmed('3')
        receipt = receive(purchase, [(purchase.items[0].id, '3')])
        receipt.set_inventory_mode(InventoryMode.DOCUMENTAL)
        with self.assertRaises(ReceiptInventoryModeAlreadySet):
            receipt.set_inventory_mode(InventoryMode.INVENTORY)
        self.assertEqual(receipt.inventory_mode, InventoryMode.DOCUMENTAL)


class ReceiveTests(TestCase):
    def test_partial_then_complete_reception_status(self):  # AC-01, AC-02, INV-06
        purchase = confirmed('10', '4')
        first, second = purchase.items
        receipt = receive(purchase, [(first.id, '4')])
        self.assertEqual((purchase.reception_status, receipt.status), (ReceptionStatus.PARTIAL, ReceiptStatus.CONFIRMED))
        self.assertEqual([(l.purchase_item_id, l.quantity) for l in receipt.lines], [(first.id, Decimal('4.000'))])
        self.assertEqual(receipt.purchase_id, purchase.id)
        receive(purchase, [(first.id, '6'), (second.id, '4')], before={first.id: Decimal('4')})
        self.assertEqual(purchase.reception_status, ReceptionStatus.RECEIVED)

    def test_receiving_everything_at_once_is_complete(self):  # EDGE-01
        purchase = confirmed('3')
        receive(purchase, [(purchase.items[0].id, '3')])
        self.assertEqual(purchase.reception_status, ReceptionStatus.RECEIVED)

    def test_payment_status_does_not_matter(self):  # INV-06, INV-12
        purchase = confirmed('3')
        receive(purchase, [(purchase.items[0].id, '1')])
        self.assertEqual(purchase.payment_status, PaymentStatus.UNPAID)

    def test_only_a_confirmed_purchase_receives(self):  # INV-01, AC-06
        draft_purchase = make([draft('1')])
        with self.assertRaises(PurchaseNotReceivable):
            receive(draft_purchase, [(draft_purchase.items[0].id, '1')])
        cancelled = confirmed('1')
        cancelled.cancel('x', NOW)
        with self.assertRaises(PurchaseNotReceivable):
            receive(cancelled, [(cancelled.items[0].id, '1')])

    def test_rejects_zero_negative_and_non_numeric_quantities(self):  # AC-03, INV-03
        purchase = confirmed('5')
        item = purchase.items[0]
        for bad in ('0', '-1', 'abc', '', '1.0005', None, 1.5):
            with self.assertRaises(PurchaseValidationError, msg=repr(bad)) as ctx:
                receive(purchase, [(item.id, bad)])
            self.assertIn('quantity', ctx.exception.errors['lines'][0])
        self.assertEqual(purchase.reception_status, ReceptionStatus.NOT_RECEIVED)

    def test_cannot_exceed_the_pending_quantity(self):  # AC-03, INV-02
        purchase = confirmed('5')
        item = purchase.items[0]
        with self.assertRaises(PurchaseValidationError) as ctx:
            receive(purchase, [(item.id, '2')], before={item.id: Decimal('4')})
        self.assertIn('pendiente (1.000)', ctx.exception.errors['lines'][0]['quantity'][0])
        self.assertEqual(purchase.reception_status, ReceptionStatus.NOT_RECEIVED)

    def test_fractions_follow_the_unit(self):  # EDGE-06
        purchase = confirmed('5')
        drafts = [ReceiptLineDraft(purchase.items[0].id, '1.5', allows_fractions=False)]
        with self.assertRaises(PurchaseValidationError):
            purchase.receive(uuid4(), TODAY, TODAY, {}, drafts, USER, 'Ana')

    def test_needs_lines_without_repeats_and_known_items(self):  # AC-04, INV-04
        purchase = confirmed('5')
        item = purchase.items[0]
        with self.assertRaises(PurchaseValidationError) as ctx:
            receive(purchase, [])
        self.assertIn('lines', ctx.exception.errors)
        with self.assertRaises(PurchaseValidationError) as ctx:
            receive(purchase, [(item.id, '1'), (item.id, '1'), (uuid4(), '1'), ('no-uuid', '1')])
        lines = ctx.exception.errors['lines']
        self.assertEqual([bool(l) for l in lines], [False, True, True, True])

    def test_date_is_required_valid_and_not_in_the_future(self):  # AC-05, INV-05
        purchase = confirmed('5')
        item = purchase.items[0]
        for bad in (None, '2026-10-30', datetime(2026, 10, 30), date(2026, 10, 31)):
            with self.assertRaises(PurchaseValidationError, msg=repr(bad)) as ctx:
                receive(purchase, [(item.id, '1')], receipt_date=bad)
            self.assertIn('receipt_date', ctx.exception.errors)
        receive(purchase, [(item.id, '1')], receipt_date=date(2020, 1, 1))  # sin cota inferior (H-04)

    def test_errors_are_reported_together(self):
        purchase = confirmed('5')
        with self.assertRaises(PurchaseValidationError) as ctx:
            receive(purchase, [(purchase.items[0].id, '0')], receipt_date=None)
        self.assertEqual(set(ctx.exception.errors), {'receipt_date', 'lines'})

    def test_allowed_actions_follow_the_reception(self):  # AC-12
        purchase = confirmed('2')
        self.assertEqual(purchase.allowed_actions, ['receive', 'pay', 'cancel'])
        receive(purchase, [(purchase.items[0].id, '1')])
        self.assertEqual(purchase.allowed_actions, ['receive', 'pay'])
        receive(purchase, [(purchase.items[0].id, '1')], before={purchase.items[0].id: Decimal('1')})
        self.assertEqual(purchase.allowed_actions, ['pay'])
        self.assertEqual(make([draft('1')]).allowed_actions, ['edit', 'confirm', 'cancel'])

    def test_the_reference_is_derived_from_the_id(self):  # H-01
        purchase = confirmed('2')
        receipt = receive(purchase, [(purchase.items[0].id, '1')])
        self.assertEqual(receipt.reference, f'REC-{receipt.id.hex[:8].upper()}')
