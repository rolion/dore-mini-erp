"""PB-COM-005: pagos y saldo de compras (BD real)."""
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.expenses.infrastructure.django.models import ExpenseModel
from modules.inventory.infrastructure.django.models import StockMovementModel
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled
from modules.purchases.infrastructure.django.models import PaymentModel, PurchaseModel
from modules.purchases.tests.test_purchase_api import LIST_URL, PurchaseApiTestCase, detail_url

PAYMENT_FIELDS = {'id', 'reference', 'amount', 'payment_method', 'payment_date', 'status', 'user_name', 'created_at'}


def purchase_url(purchase_id, suffix):
    return f'{LIST_URL}{purchase_id}/{suffix}'


class PaymentApiTestCase(PurchaseApiTestCase):
    def confirmed_purchase(self, quantity='10', unit_price='5.00'):  # total 50.00 por defecto
        created = self.client.post(LIST_URL, {
            'supplier_id': str(self.supplier.id), 'purchase_date': '2026-10-20',
            'items': [{'product_id': str(self.flour.id), 'quantity': quantity, 'unit_price': unit_price}]},
            format='json').json()
        response = self.client.post(purchase_url(created['id'], 'confirm/'), format='json')
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def pay(self, purchase, amount='20.00', expected=201, payment_id=None, **extra):
        body = {'payment_id': str(payment_id or uuid4()), 'amount': amount, 'payment_method': 'CASH',
                'payment_date': timezone.localdate().isoformat(), **extra}
        response = self.client.post(purchase_url(purchase['id'], 'payments/'), body, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def detail(self, purchase):
        return self.client.get(detail_url(purchase['id'])).json()


class RegisterPaymentTests(PaymentApiTestCase):
    def test_partial_then_full_payment(self):  # AC-01, AC-02, AC-11
        purchase = self.confirmed_purchase()
        self.assertEqual((purchase['paid_total'], purchase['balance'], purchase['payment_status']),
                         ('0.00', '50.00', 'unpaid'))
        body = self.pay(purchase, '20.00', payment_method='QR')
        self.assertEqual(set(body), PAYMENT_FIELDS)
        self.assertRegex(body['reference'], r'^PAG-[0-9A-F]{8}$')
        self.assertEqual((body['amount'], body['payment_method'], body['status'], body['user_name']),
                         ('20.00', 'QR', 'confirmed', 'ana'))
        detail = self.detail(purchase)
        self.assertEqual((detail['paid_total'], detail['balance'], detail['payment_status']),
                         ('20.00', '30.00', 'partial'))
        self.pay(purchase, '30.00')
        detail = self.detail(purchase)
        self.assertEqual((detail['paid_total'], detail['balance'], detail['payment_status']),
                         ('50.00', '0.00', 'paid'))
        self.assertEqual(detail['reception_status'], 'not_received')

    def test_invalid_amounts_are_rejected(self):  # AC-03, EDGE-04
        purchase = self.confirmed_purchase()
        for bad in (None, '', 'abc', '0', '-5', '10.005', 1.5, True, '1e3', 'NaN', 'Infinity', [1], {'a': 1}):
            body = {'payment_id': str(uuid4()), 'amount': bad, 'payment_method': 'CASH',
                    'payment_date': timezone.localdate().isoformat()}
            response = self.client.post(purchase_url(purchase['id'], 'payments/'), body, format='json')
            self.assertEqual(response.status_code, 400, bad)
            self.assertIn('amount', response.json(), bad)
        self.assertEqual(PaymentModel.objects.count(), 0)

    def test_overpayment_is_rejected_with_the_balance(self):  # AC-03
        purchase = self.confirmed_purchase()
        self.pay(purchase, '40.00')
        body = self.pay(purchase, '10.01', expected=400)
        self.assertIn('saldo pendiente (10.00)', body['amount'][0])
        self.assertEqual(PaymentModel.objects.count(), 1)

    def test_method_and_date_are_validated_together(self):  # AC-04
        purchase = self.confirmed_purchase()
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        body = self.pay(purchase, '0', expected=400, payment_method='CHEQUE', payment_date=tomorrow)
        self.assertEqual(set(body), {'amount', 'payment_method', 'payment_date'})
        body = self.pay(purchase, '1.00', expected=400, payment_method=None, payment_date=None)
        self.assertEqual(set(body), {'payment_method', 'payment_date'})
        self.assertEqual(self.pay(purchase, '1.00', expected=400, payment_id='no-uuid').keys(), {'payment_id'})

    def test_malformed_shapes_are_reported_together_with_domain_errors(self):  # AC-04, REV-01
        purchase = self.confirmed_purchase()
        for bad_date in ('abc', '30/10/2026', 20261030, ['2026-10-30']):
            body = self.pay(purchase, '0', expected=400, payment_method=['CASH'], payment_date=bad_date)
            self.assertEqual(set(body), {'amount', 'payment_method', 'payment_date'}, bad_date)
        self.assertEqual(PaymentModel.objects.count(), 0)
        self.pay(purchase, '1.00', payment_date=f' {timezone.localdate().isoformat()} ')

    def test_a_deactivated_supplier_or_product_does_not_block_payment(self):  # EDGE-07
        purchase = self.confirmed_purchase()
        self.supplier.active = False
        self.supplier.save()
        self.flour.active = False
        self.flour.can_buy = False
        self.flour.save()
        self.pay(purchase, '10.00')
        self.assertEqual(self.detail(purchase)['payment_status'], 'partial')

    def test_a_purchase_confirmed_before_payments_existed_starts_unpaid(self):  # EDGE-08
        purchase = self.confirmed_purchase()
        self.assertEqual(PaymentModel.objects.count(), 0)
        detail = self.detail(purchase)
        self.assertEqual((detail['paid_total'], detail['balance'], detail['payment_status']),
                         ('0.00', detail['total'], 'unpaid'))
        self.assertEqual(self.client.get(purchase_url(purchase['id'], 'payments/')).json()['count'], 0)

    def test_only_a_confirmed_purchase_admits_payments(self):  # AC-05
        draft = self.create()
        response = self.client.post(purchase_url(draft['id'], 'payments/'), {
            'payment_id': str(uuid4()), 'amount': '1.00', 'payment_method': 'CASH',
            'payment_date': timezone.localdate().isoformat()}, format='json')
        self.assertEqual((response.status_code, response.json()['detail']),
                         (409, 'Solo una compra confirmada admite pagos.'))
        cancelled = self.create()
        self.client.post(purchase_url(cancelled['id'], 'cancel/'), {'reason': 'x'}, format='json')
        self.pay(cancelled, expected=409)
        self.assertEqual(PaymentModel.objects.count(), 0)

    def test_a_paid_purchase_has_no_balance_and_no_pay_action(self):  # AC-06, AC-09
        purchase = self.confirmed_purchase()
        self.assertEqual(purchase['allowed_actions'], ['receive', 'pay', 'cancel'])
        self.pay(purchase, '50.00')
        detail = self.detail(purchase)
        self.assertEqual(detail['allowed_actions'], ['receive'])
        body = self.pay(purchase, '1.00', expected=400)
        self.assertIn('saldo', body['amount'][0])

    def test_a_zero_total_purchase_cannot_be_paid(self):  # AC-06, EDGE-06
        purchase = self.confirmed_purchase(unit_price='0')
        self.assertNotIn('pay', purchase['allowed_actions'])
        self.pay(purchase, '1.00', expected=400)

    def test_can_pay_before_or_after_receiving_without_side_effects(self):  # AC-07
        purchase = self.confirmed_purchase()
        movements, expenses = StockMovementModel.objects.count(), ExpenseModel.objects.count()
        self.pay(purchase, '10.00')
        item = purchase['items'][0]['id']
        receipt = self.client.post(purchase_url(purchase['id'], 'receipts/'), {
            'receipt_id': str(uuid4()), 'receipt_date': timezone.localdate().isoformat(),
            'lines': [{'item_id': item, 'quantity': '10'}]}, format='json')
        self.assertEqual(receipt.status_code, 201, receipt.content)
        self.pay(purchase, '40.00')
        detail = self.detail(purchase)
        self.assertEqual((detail['reception_status'], detail['payment_status'], detail['total']),
                         ('received', 'paid', '50.00'))
        self.assertEqual((StockMovementModel.objects.count(), ExpenseModel.objects.count()), (movements, expenses))

    def test_idempotent_by_payment_id(self):  # AC-08
        purchase = self.confirmed_purchase()
        payment_id = uuid4()
        first = self.pay(purchase, '20.00', payment_id=payment_id)
        again = self.pay(purchase, '20.00', expected=200, payment_id=payment_id)
        self.assertEqual(again['id'], first['id'])
        self.assertEqual(PaymentModel.objects.count(), 1)
        self.assertEqual(self.detail(purchase)['paid_total'], '20.00')
        other = self.confirmed_purchase()
        body = self.pay(other, '1.00', expected=409, payment_id=payment_id)
        self.assertEqual(body['code'], 'payment_conflict')
        self.assertEqual(PaymentModel.objects.count(), 1)

    def test_payments_block_cancellation(self):  # AC-09
        purchase = self.confirmed_purchase()
        self.pay(purchase, '1.00')
        response = self.client.post(purchase_url(purchase['id'], 'cancel/'), {'reason': 'x'}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(PurchaseModel.objects.get(pk=purchase['id']).status, 'confirmed')

    def test_amounts_are_stored_as_decimal(self):  # AC-14
        purchase = self.confirmed_purchase()
        self.pay(purchase, '12.34')
        self.assertEqual(PaymentModel.objects.get().amount, Decimal('12.34'))


class ListPaymentsTests(PaymentApiTestCase):
    def test_list_is_paginated_and_ordered(self):  # AC-10
        purchase = self.confirmed_purchase()
        today = timezone.localdate()
        self.pay(purchase, '10.00', payment_date=(today - timedelta(days=2)).isoformat())
        newest = self.pay(purchase, '5.00', payment_date=today.isoformat())
        body = self.client.get(purchase_url(purchase['id'], 'payments/')).json()
        self.assertEqual(body['count'], 2)
        self.assertEqual([p['amount'] for p in body['results']], ['5.00', '10.00'])
        self.assertEqual(body['results'][0]['id'], newest['id'])
        self.assertEqual(set(body['results'][0]), PAYMENT_FIELDS)

    def test_empty_list_and_unknown_purchase(self):  # AC-10
        purchase = self.confirmed_purchase()
        self.assertEqual(self.client.get(purchase_url(purchase['id'], 'payments/')).json()['count'], 0)
        self.assertEqual(self.client.get(purchase_url(uuid4(), 'payments/')).status_code, 404)


class PaymentAccessTests(PaymentApiTestCase):
    def test_other_company_gets_404(self):  # AC-12
        purchase = self.confirmed_purchase()
        self.pay(purchase, '10.00')
        other = make_company('Empresa B')
        client = APIClient()
        authenticate(client, make_admin(other, username='beto'))
        set_enabled(other, DEFAULT_ENABLED_KEYS + ('purchases',))
        self.assertEqual(client.get(purchase_url(purchase['id'], 'payments/')).status_code, 404)
        response = client.post(purchase_url(purchase['id'], 'payments/'), {
            'payment_id': str(uuid4()), 'amount': '1.00', 'payment_method': 'CASH',
            'payment_date': timezone.localdate().isoformat()}, format='json')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(PaymentModel.objects.filter(company_id=other.id).count(), 0)

    def test_requires_authentication(self):  # AC-12
        purchase = self.confirmed_purchase()
        self.assertEqual(APIClient().get(purchase_url(purchase['id'], 'payments/')).status_code, 401)
        self.assertEqual(APIClient().post(purchase_url(purchase['id'], 'payments/'), {}, format='json').status_code,
                         401)

    def test_module_disabled_is_forbidden(self):  # AC-12
        purchase = self.confirmed_purchase()
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)
        response = self.client.get(purchase_url(purchase['id'], 'payments/'))
        self.assertEqual((response.status_code, response.json().get('code')), (403, 'module_disabled'))

    def test_unsupported_methods(self):  # AC-12
        purchase = self.confirmed_purchase()
        url = purchase_url(purchase['id'], 'payments/')
        for method in (self.client.put, self.client.patch, self.client.delete):
            self.assertEqual(method(url, {}, format='json').status_code, 405)
