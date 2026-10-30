from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from modules.purchases.application.payment_commands import RegisterPayment
from modules.purchases.application.payment_queries import ListPayments
from modules.purchases.application.ports import Actor
from modules.purchases.application.purchase_commands import ConfirmPurchase, ItemInput
from modules.purchases.application.purchase_queries import GetPurchase
from modules.purchases.domain.enums import PaymentStatus
from modules.purchases.domain.exceptions import (
    PaymentConflict,
    PurchaseNotFound,
    PurchaseNotPayable,
    PurchaseValidationError,
)
from modules.purchases.tests.test_purchase_application import PurchaseApplicationCase

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 30)
ACTOR = Actor(uuid4(), 'Ana')


class FakePayments:
    def __init__(self):
        self.rows = {}

    def get(self, payment_id):
        return self.rows.get(payment_id)

    def save(self, payment):
        self.rows[payment.id] = payment
        return payment

    def list_for_purchase(self, purchase_id):
        return [p for p in self.rows.values() if p.purchase_id == purchase_id]

    def paid_total(self, purchase_id):
        return sum((p.amount for p in self.list_for_purchase(purchase_id)), Decimal('0.00'))


class PaymentCase(PurchaseApplicationCase):
    def setUp(self):
        super().setUp()
        self.payments = FakePayments()
        self.purchase = self.create(items=[ItemInput(self.flour.id, '10', '5.00')])  # total 50.00
        ConfirmPurchase(self.purchases, self.suppliers).execute(self.purchase.id, NOW)

    def pay(self, amount='20.00', payment_id=None, method='CASH', purchase_id=None, when=TODAY):
        return RegisterPayment(self.purchases, self.payments).execute(
            purchase_id or self.purchase.id, payment_id or uuid4(), amount, method, when, ACTOR, TODAY)


class RegisterPaymentTests(PaymentCase):
    def test_registers_and_updates_the_status(self):  # AC-01, AC-02
        payment, created = self.pay('20.00')
        self.assertTrue(created)
        self.assertEqual((payment.user_name, payment.amount), ('Ana', Decimal('20.00')))
        self.assertEqual(self.purchases.rows[self.purchase.id].payment_status, PaymentStatus.PARTIAL)
        self.pay('30.00')
        self.assertEqual(self.purchases.rows[self.purchase.id].payment_status, PaymentStatus.PAID)

    def test_accumulated_payments_cannot_exceed_the_total(self):  # AC-03, INV-03
        self.pay('40.00')
        with self.assertRaises(PurchaseValidationError) as ctx:
            self.pay('10.01')
        self.assertIn('10.00', ctx.exception.errors['amount'][0])
        self.assertEqual(len(self.payments.rows), 1)

    def test_nothing_is_saved_when_validation_fails(self):  # AC-03
        saved = self.purchases.saved
        with self.assertRaises(PurchaseValidationError):
            self.pay('0')
        self.assertEqual((len(self.payments.rows), self.purchases.saved), (0, saved))

    def test_repeating_the_payment_id_returns_the_same_payment(self):  # AC-08, INV-08
        payment_id = uuid4()
        first, created = self.pay('20.00', payment_id)
        again, created_again = self.pay('20.00', payment_id)
        self.assertEqual((created, created_again, again.id), (True, False, first.id))
        self.assertEqual(self.payments.paid_total(self.purchase.id), Decimal('20.00'))

    def test_the_id_of_another_purchase_is_a_conflict(self):  # AC-08
        other = self.create(items=[ItemInput(self.flour.id, '1', '5.00')])
        ConfirmPurchase(self.purchases, self.suppliers).execute(other.id, NOW)
        payment_id = uuid4()
        self.pay('1.00', payment_id, purchase_id=other.id)
        with self.assertRaises(PaymentConflict):
            self.pay('1.00', payment_id)

    def test_unknown_or_unconfirmed_purchase(self):  # AC-05
        with self.assertRaises(PurchaseNotFound):
            self.pay(purchase_id=uuid4())
        draft_purchase = self.create(items=[ItemInput(self.flour.id, '1', '5.00')])
        with self.assertRaises(PurchaseNotPayable):
            self.pay(purchase_id=draft_purchase.id)


class PaymentQueriesTests(PaymentCase):
    def test_list_and_unknown_purchase(self):  # AC-10
        self.pay('10.00')
        self.pay('5.00')
        self.assertEqual(len(ListPayments(self.purchases, self.payments).execute(self.purchase.id)), 2)
        with self.assertRaises(PurchaseNotFound):
            ListPayments(self.purchases, self.payments).execute(uuid4())

    def test_detail_exposes_paid_total_and_balance(self):  # AC-11
        self.pay('12.50')
        detail = GetPurchase(self.purchases, self.suppliers, payments=self.payments).execute(self.purchase.id)
        self.assertEqual((detail.paid_total, detail.balance), (Decimal('12.50'), Decimal('37.50')))
