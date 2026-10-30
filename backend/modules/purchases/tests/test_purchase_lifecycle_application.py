from datetime import datetime, timezone
from uuid import uuid4

from modules.purchases.application.purchase_commands import CancelPurchase, ConfirmPurchase
from modules.purchases.domain.enums import PaymentStatus, PurchaseStatus
from modules.purchases.domain.exceptions import (
    PurchaseCancellationBlocked,
    PurchaseNotFound,
    PurchaseValidationError,
)
from modules.purchases.tests.test_purchase_application import PurchaseApplicationCase

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


class ConfirmPurchaseTests(PurchaseApplicationCase):
    def confirm(self, purchase, now=NOW):
        return ConfirmPurchase(self.purchases, self.suppliers).execute(purchase.id, now)

    def test_confirms_a_valid_draft(self):  # AC-01
        purchase = self.confirm(self.create())
        self.assertEqual((purchase.status, purchase.confirmed_at), (PurchaseStatus.CONFIRMED, NOW))

    def test_inactive_supplier_and_no_items_are_reported_together(self):  # AC-02, EDGE-01
        purchase = self.create(items=[])
        self.supplier.active = False
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.confirm(purchase)
        self.assertEqual(set(ctx.exception.errors), {'supplier_id', 'items'})
        self.assertEqual(self.purchases.rows[purchase.id].status, PurchaseStatus.DRAFT)

    def test_repeating_does_not_change_or_save_again(self):  # AC-04
        purchase = self.confirm(self.create())
        saved = self.purchases.saved
        again = self.confirm(purchase, LATER)
        self.assertEqual((again.confirmed_at, self.purchases.saved), (NOW, saved))

    def test_unknown_purchase(self):
        with self.assertRaises(PurchaseNotFound):
            ConfirmPurchase(self.purchases, self.suppliers).execute(uuid4(), NOW)

    def test_inactive_product_does_not_block(self):  # EDGE-02
        purchase = self.create()
        self.products.rows.clear()  # el catálogo ya no lo ofrece: confirmar no lo revalida
        self.assertEqual(self.confirm(purchase).status, PurchaseStatus.CONFIRMED)


class CancelPurchaseTests(PurchaseApplicationCase):
    def cancel(self, purchase, reason='Error de carga', now=NOW):
        return CancelPurchase(self.purchases).execute(purchase.id, reason, now)

    def test_cancels_draft_and_confirmed(self):  # AC-05, AC-06
        cancelled_draft = self.cancel(self.create())
        confirmed = ConfirmPurchase(self.purchases, self.suppliers).execute(self.create().id, NOW)
        self.cancel(confirmed)
        self.assertEqual((cancelled_draft.status, confirmed.status),
                         (PurchaseStatus.CANCELLED, PurchaseStatus.CANCELLED))

    def test_reason_is_required(self):  # AC-07
        purchase = self.create()
        with self.assertRaises(PurchaseValidationError):
            self.cancel(purchase, reason='  ')
        self.assertEqual(purchase.status, PurchaseStatus.DRAFT)

    def test_blocked_by_activity(self):  # AC-08
        purchase = ConfirmPurchase(self.purchases, self.suppliers).execute(self.create().id, NOW)
        purchase.payment_status = PaymentStatus.PARTIAL
        with self.assertRaises(PurchaseCancellationBlocked):
            self.cancel(purchase)
        self.assertEqual(purchase.status, PurchaseStatus.CONFIRMED)

    def test_repeating_keeps_original_reason_and_date(self):  # AC-09, AC-12
        purchase = self.cancel(self.create(), 'Primera')
        saved = self.purchases.saved
        again = self.cancel(purchase, 'Otra', LATER)
        self.assertEqual((again.cancellation_reason, again.cancelled_at, self.purchases.saved), ('Primera', NOW, saved))
