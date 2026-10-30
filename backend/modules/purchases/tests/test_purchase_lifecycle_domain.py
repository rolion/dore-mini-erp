from datetime import datetime, timezone
from unittest import TestCase

from modules.purchases.domain.enums import PaymentStatus, PurchaseStatus, ReceptionStatus
from modules.purchases.domain.exceptions import (
    PurchaseCancellationBlocked,
    PurchaseInvalidTransition,
    PurchaseNotEditable,
    PurchaseValidationError,
)
from modules.purchases.tests.test_purchase_domain import draft, make

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


class LifecycleTests(TestCase):
    def test_confirm_locks_the_draft(self):  # INV-01, INV-03
        purchase = make([draft()])
        purchase.confirm(NOW)
        self.assertEqual((purchase.status, purchase.confirmed_at, purchase.editable),
                         (PurchaseStatus.CONFIRMED, NOW, False))
        self.assertEqual(purchase.allowed_actions, ['cancel'])
        with self.assertRaises(PurchaseNotEditable):
            purchase.update(notes='x')

    def test_confirm_needs_items_and_an_active_supplier_reported_together(self):  # INV-01, INV-02
        purchase = make()
        with self.assertRaises(PurchaseValidationError) as ctx:
            purchase.confirm(NOW, supplier_active=False)
        self.assertEqual(set(ctx.exception.errors), {'items', 'supplier_id'})
        self.assertEqual(purchase.status, PurchaseStatus.DRAFT)

    def test_only_a_draft_confirms(self):  # INV-06
        purchase = make([draft()])
        purchase.cancel('error', NOW)
        with self.assertRaises(PurchaseInvalidTransition):
            purchase.confirm(NOW)

    def test_cancel_requires_a_trimmed_reason_up_to_500(self):  # INV-04, EDGE-04
        for reason in (None, '', '   ', 'x' * 501):
            purchase = make([draft()])
            with self.assertRaises(PurchaseValidationError) as ctx:
                purchase.cancel(reason, NOW)
            self.assertIn('reason', ctx.exception.errors)
            self.assertEqual(purchase.status, PurchaseStatus.DRAFT)
        purchase = make([draft()])
        purchase.cancel('  ' + 'x' * 500 + '  ', NOW)
        self.assertEqual(purchase.cancellation_reason, 'x' * 500)
        self.assertEqual((purchase.status, purchase.cancelled_at, purchase.allowed_actions),
                         (PurchaseStatus.CANCELLED, NOW, []))

    def test_cancel_a_confirmed_purchase_without_activity(self):  # INV-04
        purchase = make([draft()])
        purchase.confirm(NOW)
        purchase.cancel('Proveedor no entrega', NOW)
        self.assertEqual(purchase.status, PurchaseStatus.CANCELLED)

    def test_cancel_is_blocked_by_receptions_or_payments(self):  # INV-05
        for field, value in (('reception_status', ReceptionStatus.PARTIAL), ('payment_status', PaymentStatus.PAID)):
            purchase = make([draft()])
            purchase.confirm(NOW)
            setattr(purchase, field, value)
            self.assertEqual(purchase.allowed_actions, [])
            with self.assertRaises(PurchaseCancellationBlocked):
                purchase.cancel('x', NOW)
            self.assertEqual(purchase.status, PurchaseStatus.CONFIRMED)

    def test_cancelled_is_terminal(self):  # INV-06
        purchase = make([draft()])
        purchase.cancel('a', NOW)
        with self.assertRaises(PurchaseInvalidTransition):
            purchase.cancel('b', NOW)
        with self.assertRaises(PurchaseNotEditable):
            purchase.update(notes='x')

    def test_draft_actions_initial_statuses_and_reference(self):  # INV-10
        purchase = make([draft()])
        self.assertEqual(purchase.allowed_actions, ['edit', 'confirm', 'cancel'])
        self.assertEqual((purchase.reception_status, purchase.payment_status),
                         (ReceptionStatus.NOT_RECEIVED, PaymentStatus.UNPAID))
        self.assertRegex(purchase.reference, r'^COM-[0-9A-F]{8}$')
