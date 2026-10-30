from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from modules.purchases.domain.enums import PaymentMethod, PaymentRecordStatus, PaymentStatus, ReceptionStatus
from modules.purchases.domain.exceptions import (
    PurchaseCancellationBlocked,
    PurchaseNotPayable,
    PurchaseValidationError,
)
from modules.purchases.tests.test_purchase_domain import draft, make

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 30)
USER = uuid4()


def confirmed(total='100.00'):
    purchase = make([draft('1', total)])
    purchase.confirm(NOW)
    return purchase


def pay(purchase, amount='40.00', method='CASH', when=TODAY, before='0.00'):
    return purchase.register_payment(uuid4(), amount, method, when, TODAY, Decimal(before), USER, 'Ana')


class RegisterPaymentTests(TestCase):
    def errors_of(self, purchase, **kwargs):
        with self.assertRaises(PurchaseValidationError) as ctx:
            pay(purchase, **kwargs)
        return ctx.exception.errors

    def test_a_payment_records_amount_method_date_and_user(self):  # AC-01, INV-02
        purchase = confirmed()
        payment = pay(purchase, '40.00', 'QR')
        self.assertEqual((payment.amount, payment.payment_method, payment.payment_date, payment.user_name),
                         (Decimal('40.00'), PaymentMethod.QR, TODAY, 'Ana'))
        self.assertEqual((payment.status, payment.purchase_id), (PaymentRecordStatus.CONFIRMED, purchase.id))
        self.assertRegex(payment.reference, r'^PAG-[0-9A-F]{8}$')  # H-01

    def test_status_goes_partial_then_paid(self):  # AC-02, INV-06, EDGE-01
        purchase = confirmed()
        self.assertEqual(purchase.payment_status, PaymentStatus.UNPAID)
        pay(purchase, '40.00')
        self.assertEqual(purchase.payment_status, PaymentStatus.PARTIAL)
        pay(purchase, '60.00', before='40.00')
        self.assertEqual(purchase.payment_status, PaymentStatus.PAID)

    def test_exact_full_payment_is_paid(self):  # EDGE-01
        purchase = confirmed()
        pay(purchase, '100.00')
        self.assertEqual(purchase.payment_status, PaymentStatus.PAID)

    def test_payment_does_not_touch_reception_total_or_items(self):  # INV-10
        purchase = confirmed()
        before = (purchase.total, len(purchase.items))
        pay(purchase, '10.00')
        self.assertEqual((purchase.total, len(purchase.items)), before)
        self.assertEqual(purchase.reception_status, ReceptionStatus.NOT_RECEIVED)

    def test_amount_must_be_positive_decimal_with_two_places(self):  # AC-03, INV-02, EDGE-04
        purchase = confirmed()
        for bad in (None, '', 'abc', '0', '0.00', '-1', '10.005', 1.5, True, '1e3', '1,5'):
            self.assertIn('amount', self.errors_of(purchase, amount=bad), bad)
        self.assertEqual(purchase.payment_status, PaymentStatus.UNPAID)

    def test_overpayment_is_rejected_with_the_balance(self):  # AC-03, INV-03
        purchase = confirmed()
        self.assertIn('saldo pendiente (100.00)', self.errors_of(purchase, amount='100.01')['amount'][0])
        self.assertIn('saldo pendiente (60.00)', self.errors_of(purchase, amount='60.01', before='40.00')['amount'][0])
        self.assertEqual(purchase.payment_status, PaymentStatus.UNPAID)

    def test_no_balance_rejects_any_payment(self):  # AC-06
        self.assertIn('saldo', self.errors_of(confirmed(), amount='1.00', before='100.00')['amount'][0])

    def test_method_must_be_in_the_catalog(self):  # AC-04, INV-04
        purchase = confirmed()
        for bad in (None, '', 'cash', 'CHEQUE', 3):
            self.assertIn('payment_method', self.errors_of(purchase, method=bad), bad)
        for good in ('CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'):
            pay(confirmed(), '1.00', good)

    def test_date_is_required_valid_and_not_future(self):  # AC-04, INV-05
        purchase = confirmed()
        self.assertIn('payment_date', self.errors_of(purchase, when=None))
        self.assertIn('payment_date', self.errors_of(purchase, when='2026-10-30'))
        self.assertIn('payment_date', self.errors_of(purchase, when=TODAY + timedelta(days=1)))
        old = TODAY - timedelta(days=400)
        self.assertEqual(pay(purchase, when=old).payment_date, old)

    def test_field_errors_are_reported_together(self):  # AC-04
        self.assertEqual(set(self.errors_of(confirmed(), amount='0', method=None, when=None)),
                         {'amount', 'payment_method', 'payment_date'})

    def test_only_a_confirmed_purchase_admits_payments(self):  # AC-05, INV-01
        with self.assertRaises(PurchaseNotPayable):
            pay(make([draft('1', '10.00')]))
        cancelled = make([draft('1', '10.00')])
        cancelled.cancel('x', NOW)
        with self.assertRaises(PurchaseNotPayable):
            pay(cancelled)

    def test_a_zero_total_purchase_has_no_balance(self):  # INV-11, EDGE-06
        purchase = confirmed('0')
        self.assertFalse(purchase.can_pay)
        self.assertNotIn('pay', purchase.allowed_actions)
        self.assertIn('amount', self.errors_of(purchase, amount='1.00'))
        self.assertEqual(purchase.payment_status, PaymentStatus.UNPAID)
        self.assertIn('cancel', purchase.allowed_actions)

    def test_allowed_actions_and_cancellation_follow_payments(self):  # AC-09
        purchase = confirmed()
        self.assertEqual(purchase.allowed_actions, ['receive', 'pay', 'cancel'])
        pay(purchase, '40.00')
        self.assertEqual(purchase.allowed_actions, ['receive', 'pay'])
        with self.assertRaises(PurchaseCancellationBlocked):
            purchase.cancel('x', NOW)
        pay(purchase, '60.00', before='40.00')
        self.assertEqual(purchase.allowed_actions, ['receive'])
        self.assertNotIn('pay', make([draft('1', '10.00')]).allowed_actions)

    def test_amounts_are_decimal(self):  # AC-14
        payment = pay(confirmed(), 40)
        self.assertIsInstance(payment.amount, Decimal)
        self.assertEqual(payment.amount, Decimal('40.00'))
