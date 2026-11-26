"""Numeración correlativa de compras (TASK-numeracion-correlativa-compras): dominio y casos de uso sin BD."""
from datetime import datetime, timezone
from uuid import UUID

from django.test import SimpleTestCase

from modules.purchases.application.purchase_commands import CancelPurchase, ConfirmPurchase
from modules.purchases.domain.enums import PurchaseStatus
from modules.purchases.domain.exceptions import (
    PurchaseInvalidTransition,
    PurchaseNumberingRejected,
    PurchaseValidationError,
)
from modules.purchases.domain.purchase import PurchaseNumber, provisional_reference
from modules.purchases.tests.test_purchase_application import PurchaseApplicationCase
from modules.purchases.tests.test_purchase_domain import draft, make

from .numbering_support import FakeNumbering

PERIOD = UUID('00000000-0000-4000-8000-0000000000bb')
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


class PurchaseNumberTests(SimpleTestCase):
    def test_code_uses_nc_prefix_with_six_digits(self):  # AC-01
        self.assertEqual(PurchaseNumber(PERIOD, '2026', 1).code, 'NC-000001')
        self.assertEqual(PurchaseNumber(PERIOD, '2026', 123456).code, 'NC-123456')

    def test_code_keeps_growing_past_six_digits(self):  # EDGE-04
        self.assertEqual(PurchaseNumber(PERIOD, '2026', 1_000_000).code, 'NC-1000000')

    def test_a_draft_shows_the_provisional_reference(self):  # AC-02
        purchase = make([draft()])
        self.assertIsNone(purchase.number)
        self.assertEqual(purchase.reference, provisional_reference(purchase.id))
        self.assertTrue(purchase.reference.startswith('COM-'))

    def test_confirming_assigns_the_number_and_the_reference(self):  # AC-01, INV-04
        purchase = make([draft()])
        purchase.confirm(NOW, PurchaseNumber(PERIOD, 'Gestión 2026', 7))
        self.assertEqual((purchase.status, purchase.reference, purchase.number.period_name),
                         (PurchaseStatus.CONFIRMED, 'NC-000007', 'Gestión 2026'))

    def test_cancelling_keeps_the_number(self):  # AC-03, INV-03
        purchase = make([draft()])
        purchase.confirm(NOW, PurchaseNumber(PERIOD, '2026', 3))
        purchase.cancel('error', NOW)
        self.assertEqual((purchase.status, purchase.reference), (PurchaseStatus.CANCELLED, 'NC-000003'))

    def test_a_second_confirmation_does_not_change_the_number(self):  # INV-03
        purchase = make([draft()])
        first = PurchaseNumber(PERIOD, '2026', 1)
        purchase.confirm(NOW, first)
        with self.assertRaises(PurchaseInvalidTransition):
            purchase.confirm(NOW, PurchaseNumber(PERIOD, '2026', 2))
        self.assertEqual(purchase.number, first)

    def test_an_invalid_purchase_is_not_numbered(self):  # INV-06
        purchase = make()
        with self.assertRaises(PurchaseValidationError):
            purchase.ensure_confirmable(supplier_active=False)
        self.assertIsNone(purchase.number)


class ConfirmPurchaseNumberingTests(PurchaseApplicationCase):
    def confirm(self, purchase, numbering):
        return ConfirmPurchase(self.purchases, self.suppliers, numbering).execute(purchase.id, NOW)

    def test_confirming_numbers_with_the_period_of_the_purchase_date(self):  # AC-04
        numbering = FakeNumbering()
        purchase = self.create()
        confirmed = self.confirm(purchase, numbering)
        self.assertEqual(numbering.calls, [purchase.purchase_date])
        self.assertTrue(confirmed.reference.startswith('NC-'))
        self.assertEqual(self.purchases.rows[purchase.id].number, confirmed.number)

    def test_a_missing_or_closed_period_leaves_the_draft_unsaved(self):  # AC-05, AC-06
        for code in ('fiscal_period_missing', 'fiscal_period_closed'):
            purchase = self.create()
            saved = self.purchases.saved
            numbering = FakeNumbering(error=PurchaseNumberingRejected(code, 'sin período'))
            with self.assertRaises(PurchaseNumberingRejected) as caught:
                self.confirm(purchase, numbering)
            self.assertEqual(caught.exception.code, code)
            stored = self.purchases.rows[purchase.id]
            self.assertEqual((stored.status, stored.number, self.purchases.saved), (PurchaseStatus.DRAFT, None, saved))

    def test_an_invalid_confirmation_does_not_consume_a_number(self):  # INV-02, AC-02
        numbering = FakeNumbering()
        purchase = self.create(items=[])
        with self.assertRaises(PurchaseValidationError):
            self.confirm(purchase, numbering)
        self.assertEqual(numbering.calls, [])

    def test_repeating_on_a_confirmed_purchase_keeps_the_number_and_consumes_none(self):  # EDGE-01
        numbering = FakeNumbering()
        purchase = self.create()
        first = self.confirm(purchase, numbering)
        again = self.confirm(purchase, numbering)
        self.assertEqual((again.number, len(numbering.calls)), (first.number, 1))

    def test_a_cancelled_after_confirming_keeps_its_number(self):  # AC-03
        purchase = self.confirm(self.create(), FakeNumbering())
        cancelled = CancelPurchase(self.purchases).execute(purchase.id, 'error', NOW)
        self.assertEqual((cancelled.status, cancelled.number), (PurchaseStatus.CANCELLED, purchase.number))
