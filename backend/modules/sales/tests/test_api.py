from datetime import timedelta
from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from modules.catalog.infrastructure.django.models import ProductModel
from modules.customers.infrastructure.django.models import CustomerModel
from modules.sales.infrastructure.django.models import OrderModel
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository

LIST_URL = '/api/orders/'

DETAIL_KEYS = {
    'id', 'code', 'customer', 'sales_channel', 'order_date', 'expected_delivery_date', 'delivered_date', 'notes',
    'status', 'payment_status', 'items', 'subtotal', 'discount', 'total', 'paid_total', 'balance', 'payments',
    'cancellation_reason', 'cancelled_at', 'editable', 'allowed_transitions', 'can_register_payment',
    'created_at', 'updated_at',
}
SUMMARY_KEYS = {
    'id', 'code', 'customer', 'sales_channel', 'order_date', 'expected_delivery_date', 'status', 'payment_status',
    'total', 'paid_total', 'balance',
}


def url(order_id, suffix=''):
    return f'/api/orders/{order_id}/{suffix}'


def today():
    return timezone.localdate()


class SalesApiTestCase(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='ana', password='x-Pass-123')
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    # --- fixtures ---
    def product(self, name='Pack cuñapé', price='35.00', active=True):
        return ProductModel.objects.create(name=name, description='', sale_price=Decimal(price), active=active)

    def customer(self, name='Ana Pérez', active=True):
        return CustomerModel.objects.create(name=name, active=active)

    def create(self, expected_status=201, **extra):
        body = {'sales_channel': 'WHATSAPP', **extra}
        response = self.client.post(LIST_URL, body, format='json')
        self.assertEqual(response.status_code, expected_status, response.content)
        return response.json()

    def add_item(self, order, product=None, quantity=2, expected_status=201):
        product = product or self.product()
        response = self.client.post(url(order['id'], 'items/'), {'product_id': str(product.id), 'quantity': quantity},
                                    format='json')
        self.assertEqual(response.status_code, expected_status, response.content)
        return response.json()

    def order_with_item(self, price='35.00', quantity=2, **extra):
        order = self.create(**extra)
        return self.add_item(order, self.product(price=price), quantity)

    def act(self, order, action, body=None, expected_status=200):
        response = self.client.post(url(order['id'], f'{action}/'), body or {}, format='json')
        self.assertEqual(response.status_code, expected_status, response.content)
        return response.json()

    def pay(self, order, amount, method='CASH', expected_status=201, **extra):
        body = {'amount': amount, 'payment_method': method, **extra}
        return self.act(order, 'payments', body, expected_status)

    def get(self, order):
        return self.client.get(url(order['id'])).json()

    def conflict(self, response, code, expected_status=409):
        self.assertEqual(response.status_code, expected_status, response.content)
        self.assertEqual(response.json()['code'], code)
        self.assertTrue(response.json()['detail'])


class CreateOrderTests(SalesApiTestCase):
    def test_create_with_channel_only(self):  # AC-01
        body = self.create()
        self.assertEqual(set(body), DETAIL_KEYS)
        self.assertEqual((body['status'], body['payment_status']), ('NEW', 'PENDING'))
        self.assertEqual(body['items'], [])
        self.assertEqual((body['subtotal'], body['discount'], body['total'], body['paid_total'], body['balance']),
                         ('0.00',) * 5)
        self.assertEqual(body['order_date'], today().isoformat())
        self.assertIsNone(body['customer'])
        self.assertIsNone(body['expected_delivery_date'])
        self.assertTrue(body['code'].startswith('P-') and len(body['code']) == 10)
        self.assertEqual((body['editable'], body['allowed_transitions'], body['can_register_payment']),
                         (True, ['prepare', 'cancel'], False))

    def test_create_with_all_fields_and_customer(self):  # AC-01, AC-18
        customer = self.customer('Luis')
        body = self.create(customer_id=str(customer.id), sales_channel='INSTAGRAM', order_date='2026-10-01',
                           expected_delivery_date='2026-10-05', notes='  Sin picante ')
        self.assertEqual(body['customer'], {'id': str(customer.id), 'name': 'Luis'})
        self.assertEqual((body['sales_channel'], body['order_date'], body['expected_delivery_date'], body['notes']),
                         ('INSTAGRAM', '2026-10-01', '2026-10-05', 'Sin picante'))
        self.assertEqual(self.get(body)['customer']['name'], 'Luis')

    def test_all_channels_are_accepted(self):  # AC-08
        for channel in ('WHATSAPP', 'FACEBOOK', 'INSTAGRAM', 'STORE', 'FAIR', 'OTHER'):
            self.assertEqual(self.create(sales_channel=channel)['sales_channel'], channel)

    def test_channel_is_required_and_validated(self):  # AC-01, AC-08
        for body in ({}, {'sales_channel': ''}, {'sales_channel': 'TELEGRAM'}):
            response = self.client.post(LIST_URL, body, format='json')
            self.assertEqual(response.status_code, 400, body)
            self.assertIn('sales_channel', response.json())
        self.assertEqual(OrderModel.objects.count(), 0)

    def test_field_errors_come_together(self):  # AC-01
        response = self.client.post(LIST_URL, {'sales_channel': 'X', 'order_date': '2026-10-05',
                                               'expected_delivery_date': '2026-10-01'}, format='json')
        self.assertEqual(set(response.json()), {'sales_channel', 'expected_delivery_date'})

    def test_malformed_dates_and_ids_are_rejected(self):  # AC-01
        response = self.client.post(LIST_URL, {'sales_channel': 'STORE', 'order_date': 'ayer',
                                               'customer_id': 'no-uuid'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'order_date', 'customer_id'})

    def test_customer_must_exist_and_be_active(self):  # AC-18
        inactive = self.customer('Viejo', active=False)
        for customer_id in (uuid4(), inactive.id):
            response = self.client.post(LIST_URL, {'sales_channel': 'STORE', 'customer_id': str(customer_id)},
                                        format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('customer_id', response.json())

    def test_derived_and_state_fields_in_the_body_are_ignored(self):  # AC-06
        body = self.create(status='DELIVERED', payment_status='PAID', total='500.00', subtotal='9.00',
                           paid_total='1.00', discount='3.00', items=[{'x': 1}], delivered_date='2026-10-01',
                           cancellation_reason='x')
        self.assertEqual((body['status'], body['payment_status'], body['total'], body['discount']),
                         ('NEW', 'PENDING', '0.00', '0.00'))
        self.assertEqual((body['items'], body['delivered_date'], body['cancellation_reason']), ([], None, ''))


class AuthAndRoutingTests(SalesApiTestCase):
    def test_requires_a_token(self):  # AC-17
        anonymous = APIClient()
        order = self.create()
        for method, target in (('get', LIST_URL), ('post', LIST_URL), ('get', url(order['id'])),
                               ('post', url(order['id'], 'prepare/')), ('post', url(order['id'], 'payments/'))):
            self.assertEqual(getattr(anonymous, method)(target).status_code, 401, (method, target))

    def test_unknown_and_malformed_ids_give_404_with_detail(self):  # AC-17
        order = self.create()
        checks = [
            ('get', url(uuid4())), ('get', url('no-es-uuid')), ('patch', url(uuid4())),
            ('post', url(uuid4(), 'prepare/')), ('post', url('xyz', 'ready/')), ('post', url(uuid4(), 'deliver/')),
            ('post', url(uuid4(), 'cancel/')), ('post', url(uuid4(), 'discount/')),
            ('post', url(uuid4(), 'items/')), ('post', url(uuid4(), 'payments/')),
            ('patch', url(order['id'], f'items/{uuid4()}/')), ('delete', url(order['id'], f'items/{uuid4()}/')),
            ('patch', url(order['id'], 'items/xyz/')),
        ]
        for method, target in checks:
            response = getattr(self.client, method)(target, {'quantity': 1, 'discount': '1', 'amount': '1',
                                                             'product_id': str(uuid4()), 'reason': 'x'}, format='json')
            self.assertEqual(response.status_code, 404, (method, target, response.content))
            self.assertIn('detail', response.json(), (method, target))

    def test_unsupported_methods(self):  # AC-17
        order = self.create()
        self.assertEqual(self.client.delete(url(order['id'])).status_code, 405)
        self.assertEqual(self.client.put(url(order['id']), {}, format='json').status_code, 405)
        self.assertEqual(self.client.get(url(order['id'], 'payments/')).status_code, 405)
        self.assertEqual(self.client.delete(url(order['id'], 'payments/')).status_code, 405)


class ItemTests(SalesApiTestCase):
    def test_add_item_takes_the_snapshot_and_computes_subtotals(self):  # AC-03
        product = self.product(name='Pack 10 cuñapés', price='35.00')
        body = self.add_item(self.create(), product, 2)
        item = body['items'][0]
        self.assertEqual((item['product_id'], item['product_name'], item['unit_price'], item['quantity'],
                          item['subtotal']), (str(product.id), 'Pack 10 cuñapés', '35.00', 2, '70.00'))
        self.assertEqual((body['subtotal'], body['total']), ('70.00', '70.00'))
        self.assertEqual(set(item), {'id', 'product_id', 'product_name', 'unit_price', 'quantity', 'subtotal'})

    def test_client_cannot_send_price_or_name(self):  # AC-03, INV-13
        order = self.create()
        product = self.product(price='35.00')
        response = self.client.post(url(order['id'], 'items/'), {
            'product_id': str(product.id), 'quantity': 1, 'unit_price': '0.01', 'product_name': 'Falso'}, format='json')
        item = response.json()['items'][0]
        self.assertEqual((item['unit_price'], item['product_name']), ('35.00', product.name))

    def test_snapshot_survives_catalog_changes(self):  # EDGE-02
        product = self.product(price='35.00')
        order = self.add_item(self.create(), product, 1)
        ProductModel.objects.filter(pk=product.id).update(sale_price=Decimal('99.00'), name='Otro nombre')
        item = self.get(order)['items'][0]
        self.assertEqual((item['unit_price'], item['product_name']), ('35.00', 'Pack cuñapé'))

    def test_free_product_can_be_added_and_the_order_is_settled(self):  # AC-03 (v2, REV-03), EDGE-13
        order = self.create()
        gift = self.product(name='Galleta gratis', price='0.00')
        body = self.add_item(order, gift, 2)
        item = body['items'][0]
        self.assertEqual((item['unit_price'], item['subtotal']), ('0.00', '0.00'))
        self.assertEqual((body['total'], body['balance'], body['payment_status'], body['can_register_payment']),
                         ('0.00', '0.00', 'PAID', False))
        body = self.act(self.act(self.act(body, 'prepare'), 'ready'), 'deliver')
        self.assertEqual((body['status'], body['payment_status']), ('DELIVERED', 'PAID'))

    def test_free_items_do_not_change_what_is_owed(self):  # EDGE-13
        order = self.order_with_item('35.00', 2)
        body = self.add_item(order, self.product(name='Obsequio', price='0.00'), 1)
        self.assertEqual((body['total'], body['balance'], body['payment_status']), ('70.00', '70.00', 'PENDING'))

    def test_inactive_and_unknown_products_are_rejected(self):  # AC-03
        order = self.create()
        inactive = self.product(active=False)
        for product_id in (inactive.id, uuid4()):
            response = self.client.post(url(order['id'], 'items/'), {'product_id': str(product_id), 'quantity': 1},
                                        format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('product_id', response.json())
        self.assertEqual(self.get(order)['items'], [])

    def test_invalid_quantities_are_rejected(self):  # AC-03, AC-04
        order = self.create()
        product = self.product()
        for quantity in (0, -2, 1.5, 'abc', None, True, 100001):
            response = self.client.post(url(order['id'], 'items/'), {'product_id': str(product.id),
                                                                     'quantity': quantity}, format='json')
            self.assertEqual(response.status_code, 400, quantity)
            self.assertIn('quantity', response.json(), quantity)
        self.assertEqual(self.get(order)['items'], [])

    def test_missing_fields(self):  # AC-03
        order = self.create()
        response = self.client.post(url(order['id'], 'items/'), {}, format='json')
        self.assertEqual(set(response.json()), {'product_id', 'quantity'})

    def test_same_product_twice_conflicts(self):  # AC-03
        order = self.create()
        product = self.product()
        self.add_item(order, product, 1)
        response = self.client.post(url(order['id'], 'items/'), {'product_id': str(product.id), 'quantity': 1},
                                    format='json')
        self.conflict(response, 'duplicate_product')

    def test_change_quantity_recalculates(self):  # AC-04
        order = self.order_with_item('35.00', 2)
        item = order['items'][0]
        response = self.client.patch(url(order['id'], f"items/{item['id']}/"), {'quantity': 5}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['items'][0]['subtotal'], body['subtotal'], body['total']),
                         ('175.00', '175.00', '175.00'))

    def test_change_quantity_rejects_invalid_values(self):  # AC-04
        order = self.order_with_item()
        target = url(order['id'], f"items/{order['items'][0]['id']}/")
        for quantity in (0, -1, 'x', 1.5):
            response = self.client.patch(target, {'quantity': quantity}, format='json')
            self.assertEqual(response.status_code, 400, quantity)
            self.assertIn('quantity', response.json())
        self.assertEqual(self.get(order)['items'][0]['quantity'], 2)

    def test_remove_item_recalculates_and_returns_the_order(self):  # AC-05
        order = self.order_with_item('35.00', 2)
        second = self.add_item(order, self.product(name='Chipa', price='10.00'), 1)
        response = self.client.delete(url(order['id'], f"items/{second['items'][1]['id']}/"))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((len(response.json()['items']), response.json()['total']), (1, '70.00'))

    def test_new_order_can_be_emptied(self):  # AC-02
        order = self.order_with_item()
        response = self.client.delete(url(order['id'], f"items/{order['items'][0]['id']}/"))
        self.assertEqual((response.status_code, response.json()['items'], response.json()['total']),
                         (200, [], '0.00'))

    def test_confirmed_order_cannot_lose_its_last_item(self):  # AC-02
        for steps in (['prepare'], ['prepare', 'ready']):
            order = self.order_with_item()
            for step in steps:
                self.act(order, step)
            response = self.client.delete(url(order['id'], f"items/{order['items'][0]['id']}/"))
            self.conflict(response, 'empty_order')
            self.assertEqual(len(self.get(order)['items']), 1)

    def test_amount_beyond_the_maximum_is_rejected(self):  # INV-01
        order = self.create()
        product = self.product(price='9999999999.99')
        response = self.client.post(url(order['id'], 'items/'), {'product_id': str(product.id), 'quantity': 2},
                                    format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('quantity', response.json())


class DiscountTests(SalesApiTestCase):
    def discount(self, order, value, expected_status=200):
        response = self.client.post(url(order['id'], 'discount/'), {'discount': value}, format='json')
        self.assertEqual(response.status_code, expected_status, response.content)
        return response

    def test_discount_recalculates_total_and_is_explicit(self):  # AC-07
        order = self.order_with_item('35.00', 2)
        body = self.discount(order, '10.00').json()
        self.assertEqual((body['subtotal'], body['discount'], body['total'], body['balance']),
                         ('70.00', '10.00', '60.00', '60.00'))
        self.assertEqual(self.get(order)['discount'], '10.00')

    def test_discount_accepts_numbers_and_zero_removes_it(self):  # AC-07
        order = self.order_with_item('35.00', 2)
        self.assertEqual(self.discount(order, 5.5).json()['total'], '64.50')
        self.assertEqual(self.discount(order, 0).json()['total'], '70.00')

    def test_discount_above_subtotal_is_rejected(self):  # AC-07
        order = self.order_with_item('35.00', 2)
        self.assertIn('discount', self.discount(order, '70.01', 400).json())
        self.assertEqual(self.get(order)['discount'], '0.00')

    def test_invalid_discount_values(self):  # AC-07
        order = self.order_with_item()
        for value in ('-1', 'abc', '1.005', None):
            self.assertIn('discount', self.discount(order, value, 400).json(), value)
        self.assertEqual(self.client.post(url(order['id'], 'discount/'), {}, format='json').status_code, 400)

    def test_discount_cannot_drop_the_total_below_what_was_paid(self):  # AC-07
        order = self.order_with_item('35.00', 2)
        self.pay(order, '65.00')
        self.conflict(self.discount(order, '10.00', 409), 'total_below_paid')
        self.assertEqual(self.get(order)['discount'], '0.00')

    def test_item_changes_that_break_discount_or_paid_are_rejected(self):  # AC-07, EDGE-05
        order = self.order_with_item('35.00', 2)
        item_url = url(order['id'], f"items/{order['items'][0]['id']}/")
        self.discount(order, '60.00')
        self.conflict(self.client.patch(item_url, {'quantity': 1}, format='json'), 'discount_exceeds_subtotal')
        self.conflict(self.client.delete(item_url), 'discount_exceeds_subtotal')
        self.discount(order, 0)
        self.pay(order, '40.00')
        self.conflict(self.client.patch(item_url, {'quantity': 1}, format='json'), 'total_below_paid')
        self.conflict(self.client.delete(item_url), 'total_below_paid')
        self.assertEqual(self.get(order)['items'][0]['quantity'], 2)

    def test_full_discount_leaves_a_paid_order_with_no_balance(self):  # AC-13, EDGE-04
        order = self.order_with_item('35.00', 2)
        body = self.discount(order, '70.00').json()
        self.assertEqual((body['total'], body['payment_status'], body['balance'], body['can_register_payment']),
                         ('0.00', 'PAID', '0.00', False))
        response = self.client.post(url(order['id'], 'payments/'), {'amount': '1.00', 'payment_method': 'CASH'},
                                    format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('amount', response.json())


class StateTests(SalesApiTestCase):
    def test_prepare_requires_an_item(self):  # AC-02
        order = self.create()
        self.conflict(self.client.post(url(order['id'], 'prepare/')), 'empty_order')
        self.assertEqual(self.get(order)['status'], 'NEW')

    def test_full_delivery_cycle_and_allowed_transitions(self):  # AC-09, AC-10
        order = self.order_with_item()
        self.assertEqual(order['allowed_transitions'], ['prepare', 'cancel'])
        order = self.act(order, 'prepare')
        self.assertEqual((order['status'], order['allowed_transitions']), ('IN_PREPARATION', ['ready', 'cancel']))
        order = self.act(order, 'ready')
        self.assertEqual((order['status'], order['allowed_transitions']), ('READY', ['deliver', 'cancel']))
        order = self.act(order, 'deliver')
        self.assertEqual((order['status'], order['delivered_date'], order['allowed_transitions'], order['editable']),
                         ('DELIVERED', today().isoformat(), [], False))

    def test_invalid_transitions_conflict_and_change_nothing(self):  # AC-09
        new = self.order_with_item()
        for action in ('ready', 'deliver'):
            self.conflict(self.client.post(url(new['id'], f'{action}/')), 'invalid_transition')
        self.assertEqual(self.get(new)['status'], 'NEW')
        ready = self.act(self.act(self.act(self.order_with_item(), 'prepare'), 'ready'), 'ready'
                         if False else 'deliver')
        for action in ('prepare', 'ready', 'deliver'):
            self.conflict(self.client.post(url(ready['id'], f'{action}/')), 'invalid_transition')
        self.conflict(self.client.post(url(ready['id'], 'cancel/'), {'reason': 'tarde'}, format='json'),
                      'invalid_transition')

    def test_cancelled_order_cannot_be_delivered_or_continue(self):  # AC-09
        order = self.act(self.order_with_item(), 'cancel', {'reason': 'No lo quiere'})
        for action in ('prepare', 'ready', 'deliver'):
            self.conflict(self.client.post(url(order['id'], f'{action}/')), 'invalid_transition')
        self.assertEqual(self.get(order)['status'], 'CANCELLED')

    def test_explicit_delivery_date_and_its_limits(self):  # AC-10, EDGE-07
        order = self.act(self.act(self.order_with_item(order_date='2026-10-01'), 'prepare'), 'ready')
        for bad in ((today() + timedelta(days=1)).isoformat(), '2026-09-30'):
            response = self.client.post(url(order['id'], 'deliver/'), {'delivered_date': bad}, format='json')
            self.assertEqual(response.status_code, 400, bad)
            self.assertIn('delivered_date', response.json())
        delivered = self.act(order, 'deliver', {'delivered_date': '2026-10-03'})
        self.assertEqual(delivered['delivered_date'], '2026-10-03')


class CancelTests(SalesApiTestCase):
    def test_reason_is_required(self):  # AC-11
        order = self.order_with_item()
        for body in ({}, {'reason': ''}, {'reason': '   '}, {'reason': None}, {'reason': 'x' * 501}):
            response = self.client.post(url(order['id'], 'cancel/'), body, format='json')
            self.assertEqual(response.status_code, 400, body)
            self.assertIn('reason', response.json())
        self.assertEqual(self.get(order)['status'], 'NEW')

    def test_cancel_from_every_open_state(self):  # AC-11
        for steps in ([], ['prepare'], ['prepare', 'ready']):
            order = self.order_with_item()
            for step in steps:
                order = self.act(order, step)
            cancelled = self.act(order, 'cancel', {'reason': '  Cliente desistió '})
            self.assertEqual((cancelled['status'], cancelled['cancellation_reason']), ('CANCELLED', 'Cliente desistió'))
            self.assertTrue(cancelled['cancelled_at'])
            self.assertEqual(len(cancelled['items']), 1)
            self.assertEqual((cancelled['editable'], cancelled['allowed_transitions'],
                              cancelled['can_register_payment']), (False, [], False))

    def test_payments_survive_cancellation(self):  # AC-11, EDGE-11
        order = self.order_with_item('35.00', 2)
        self.pay(order, '20.00')
        cancelled = self.act(order, 'cancel', {'reason': 'Se canceló'})
        self.assertEqual((len(cancelled['payments']), cancelled['paid_total'], cancelled['payment_status'],
                          cancelled['balance']), (1, '20.00', 'PARTIAL', '50.00'))
        self.assertEqual(self.get(order)['payments'][0]['amount'], '20.00')

    def test_no_new_payments_after_cancelling(self):  # AC-12, EDGE-11
        order = self.act(self.order_with_item(), 'cancel', {'reason': 'x'})
        response = self.client.post(url(order['id'], 'payments/'), {'amount': '1.00', 'payment_method': 'CASH'},
                                    format='json')
        self.conflict(response, 'order_cancelled')


class EditTests(SalesApiTestCase):
    def test_patch_changes_details(self):  # AC-10, AC-24
        customer = self.customer('Luis')
        order = self.create(notes='a')
        response = self.client.patch(url(order['id']), {'customer_id': str(customer.id), 'sales_channel': 'FAIR',
                                                        'expected_delivery_date': '2026-12-01'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['customer']['name'], body['sales_channel'], body['expected_delivery_date'],
                          body['notes']), ('Luis', 'FAIR', '2026-12-01', 'a'))

    def test_customer_and_delivery_date_can_be_cleared(self):  # AC-18
        order = self.create(customer_id=str(self.customer().id), expected_delivery_date='2026-12-01')
        body = self.client.patch(url(order['id']), {'customer_id': None, 'expected_delivery_date': None},
                                 format='json').json()
        self.assertEqual((body['customer'], body['expected_delivery_date']), (None, None))

    def test_expected_delivery_cannot_precede_order_date(self):  # AC-10, EDGE-06
        order = self.create(order_date='2026-10-01', expected_delivery_date='2026-10-05')
        response = self.client.patch(url(order['id']), {'order_date': '2026-10-09'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('expected_delivery_date', response.json())
        response = self.client.patch(url(order['id']), {'expected_delivery_date': '2026-09-01'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_inactive_customer_cannot_be_assigned_but_existing_one_is_kept(self):  # AC-18, EDGE-08
        customer = self.customer('Ana')
        order = self.create(customer_id=str(customer.id))
        CustomerModel.objects.filter(pk=customer.id).update(active=False)
        body = self.client.patch(url(order['id']), {'notes': 'sigue editable'}, format='json').json()
        self.assertEqual((body['customer']['name'], body['notes']), ('Ana', 'sigue editable'))
        other = self.customer('Baja', active=False)
        response = self.client.patch(url(order['id']), {'customer_id': str(other.id)}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('customer_id', response.json())

    def test_state_and_derived_fields_are_ignored_on_patch(self):  # AC-06
        order = self.order_with_item()
        body = self.client.patch(url(order['id']), {'status': 'DELIVERED', 'total': '1.00', 'payment_status': 'PAID',
                                                    'notes': 'ok'}, format='json').json()
        self.assertEqual((body['status'], body['total'], body['payment_status'], body['notes']),
                         ('NEW', '70.00', 'PENDING', 'ok'))

    def test_delivered_and_cancelled_orders_are_not_editable(self):  # AC-19
        delivered = self.act(self.act(self.act(self.order_with_item(), 'prepare'), 'ready'), 'deliver')
        cancelled = self.act(self.order_with_item(), 'cancel', {'reason': 'x'})
        for order in (delivered, cancelled):
            item_id = order['items'][0]['id']
            product = self.product(name='Otro')
            checks = [
                self.client.patch(url(order['id']), {'notes': 'x'}, format='json'),
                self.client.post(url(order['id'], 'items/'), {'product_id': str(product.id), 'quantity': 1},
                                 format='json'),
                self.client.patch(url(order['id'], f'items/{item_id}/'), {'quantity': 3}, format='json'),
                self.client.delete(url(order['id'], f'items/{item_id}/')),
                self.client.post(url(order['id'], 'discount/'), {'discount': '1.00'}, format='json'),
            ]
            for response in checks:
                self.conflict(response, 'order_not_editable')

    def test_open_orders_stay_editable_until_ready(self):  # INV-04
        order = self.order_with_item()
        for step in (None, 'prepare', 'ready'):
            if step:
                order = self.act(order, step)
            body = self.client.patch(url(order['id']), {'notes': f'en {step}'}, format='json').json()
            self.assertEqual(body['notes'], f'en {step}')
            self.assertTrue(body['editable'])


class PaymentTests(SalesApiTestCase):
    def test_register_payment(self):  # AC-12
        order = self.order_with_item('35.00', 2)
        body = self.pay(order, '20.00', 'QR', payment_date='2026-10-02', reference=' ref-1 ')
        self.assertEqual((body['paid_total'], body['balance'], body['payment_status']), ('20.00', '50.00', 'PARTIAL'))
        payment = body['payments'][0]
        self.assertEqual((payment['amount'], payment['payment_method'], payment['payment_date'],
                          payment['reference']), ('20.00', 'QR', '2026-10-02', 'ref-1'))
        self.assertEqual(set(payment), {'id', 'amount', 'payment_method', 'payment_date', 'reference', 'created_at'})
        self.assertEqual(self.get(order)['payments'][0]['id'], payment['id'])

    def test_payment_date_defaults_to_today(self):  # AC-12
        body = self.pay(self.order_with_item(), '1.00')
        self.assertEqual(body['payments'][0]['payment_date'], today().isoformat())

    def test_all_methods(self):  # AC-12
        order = self.order_with_item('100.00', 1)
        for method in ('CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'):
            body = self.pay(order, '1.00', method)
        self.assertEqual(len(body['payments']), 5)

    def test_invalid_amount_method_and_date(self):  # AC-12
        order = self.order_with_item()
        for amount in (0, '0.00', '-1', 'abc', '1.005', None):
            response = self.client.post(url(order['id'], 'payments/'), {'amount': amount, 'payment_method': 'CASH'},
                                        format='json')
            self.assertEqual(response.status_code, 400, amount)
            self.assertIn('amount', response.json(), amount)
        response = self.client.post(url(order['id'], 'payments/'), {
            'amount': '1.00', 'payment_method': 'BITCOIN', 'payment_date': (today() + timedelta(days=1)).isoformat(),
            'reference': 'r' * 101}, format='json')
        self.assertEqual(set(response.json()), {'payment_method', 'payment_date', 'reference'})
        response = self.client.post(url(order['id'], 'payments/'), {'amount': '1.00'}, format='json')
        self.assertIn('payment_method', response.json())
        self.assertEqual(self.get(order)['payments'], [])

    def test_amount_cannot_exceed_balance(self):  # AC-12, INV-10
        order = self.order_with_item('35.00', 2)
        response = self.client.post(url(order['id'], 'payments/'), {'amount': '70.01', 'payment_method': 'CASH'},
                                    format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('amount', response.json())
        self.pay(order, '70.00')
        response = self.client.post(url(order['id'], 'payments/'), {'amount': '0.01', 'payment_method': 'CASH'},
                                    format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.get(order)['payments']), 1)

    def test_second_payment_beyond_balance_is_rejected(self):  # EDGE-01
        order = self.order_with_item('35.00', 2)
        self.pay(order, '40.00')
        response = self.client.post(url(order['id'], 'payments/'), {'amount': '40.00', 'payment_method': 'CASH'},
                                    format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get(order)['paid_total'], '40.00')

    def test_payment_statuses_pending_partial_paid(self):  # AC-13
        order = self.order_with_item('35.00', 2)
        self.assertEqual(order['payment_status'], 'PENDING')
        self.assertEqual(self.pay(order, '20.00')['payment_status'], 'PARTIAL')
        paid = self.pay(order, '50.00')
        self.assertEqual((paid['payment_status'], paid['balance'], paid['can_register_payment']),
                         ('PAID', '0.00', False))

    def test_empty_order_has_no_balance_to_pay(self):  # INV-10
        order = self.create()
        response = self.client.post(url(order['id'], 'payments/'), {'amount': '1.00', 'payment_method': 'CASH'},
                                    format='json')
        self.assertEqual(response.status_code, 400)

    def test_delivered_order_with_balance_accepts_payments(self):  # AC-14, AC-15
        order = self.act(self.act(self.act(self.order_with_item('35.00', 2), 'prepare'), 'ready'), 'deliver')
        self.assertEqual((order['status'], order['payment_status'], order['balance']), ('DELIVERED', 'PENDING', '70.00'))
        self.assertTrue(order['can_register_payment'])
        partial = self.pay(order, '30.00')
        self.assertEqual((partial['status'], partial['payment_status'], partial['balance']),
                         ('DELIVERED', 'PARTIAL', '40.00'))
        done = self.pay(order, '40.00')
        self.assertEqual((done['status'], done['payment_status'], done['balance']), ('DELIVERED', 'PAID', '0.00'))

    def test_paid_order_can_still_be_delivered(self):  # AC-15
        order = self.order_with_item('35.00', 2)
        self.assertEqual(self.pay(order, '70.00')['status'], 'NEW')
        order = self.act(self.act(self.act(order, 'prepare'), 'ready'), 'deliver')
        self.assertEqual((order['status'], order['payment_status']), ('DELIVERED', 'PAID'))

    def test_delivery_and_payment_axes_do_not_touch_each_other(self):  # AC-15
        order = self.order_with_item()
        after_prepare = self.act(order, 'prepare')
        self.assertEqual(after_prepare['payment_status'], 'PENDING')
        after_payment = self.pay(order, '10.00')
        self.assertEqual(after_payment['status'], 'IN_PREPARATION')

    def test_mutations_run_inside_a_transaction_with_a_row_lock(self):  # AC-20
        order = self.order_with_item()
        depths = []
        original = DjangoOrderRepository.get_for_update

        def spy(repository, order_id):
            depths.append(len(connection.savepoint_ids))
            return original(repository, order_id)

        with mock.patch.object(DjangoOrderRepository, 'get_for_update', spy):
            self.pay(order, '1.00')
            self.act(order, 'prepare')
        self.assertEqual(len(depths), 2)
        self.assertTrue(all(depth >= 1 for depth in depths), depths)


class DetailTests(SalesApiTestCase):
    def test_detail_has_everything_needed_to_operate(self):  # AC-17
        customer = self.customer('Luis')
        order = self.order_with_item('35.00', 2, customer_id=str(customer.id), expected_delivery_date='2030-01-01',
                                     notes='Nota')
        self.pay(order, '20.00', 'QR')
        body = self.get(order)
        self.assertEqual(set(body), DETAIL_KEYS)
        self.assertEqual(body['customer'], {'id': str(customer.id), 'name': 'Luis'})
        self.assertEqual((body['status'], body['payment_status'], body['total'], body['paid_total'], body['balance']),
                         ('NEW', 'PARTIAL', '70.00', '20.00', '50.00'))
        self.assertEqual((len(body['items']), len(body['payments']), body['notes']), (1, 1, 'Nota'))
        self.assertEqual((body['editable'], body['can_register_payment']), (True, True))

    def test_amounts_are_decimal_strings(self):  # AC-06
        body = self.order_with_item('12.50', 3)
        for key in ('subtotal', 'discount', 'total', 'paid_total', 'balance'):
            self.assertIsInstance(body[key], str, key)
        self.assertEqual(body['total'], '37.50')


class ListTests(SalesApiTestCase):
    def setUp(self):
        super().setUp()
        self.ana = self.customer('Ana')
        self.luis = self.customer('Luis', active=False)
        self.o1 = self.order_with_item('35.00', 2, customer_id=str(self.ana.id), order_date='2026-10-01',
                                       expected_delivery_date='2026-10-12', sales_channel='WHATSAPP')
        self.o2 = self.order_with_item('35.00', 2, order_date='2026-10-03', expected_delivery_date='2026-10-09',
                                       sales_channel='STORE')
        self.pay(self.o2, '70.00')
        self.o3 = self.order_with_item('35.00', 2, order_date='2026-10-05', sales_channel='FAIR')
        self.pay(self.o3, '10.00')
        self.o4 = self.act(self.order_with_item('35.00', 2, order_date='2026-10-07', sales_channel='FACEBOOK',
                                                expected_delivery_date='2026-10-08'),
                           'cancel', {'reason': 'x'})
        self.o5 = self.act(self.act(self.act(self.order_with_item('35.00', 2, order_date='2026-10-04',
                                                                  customer_id=str(self.ana.id)), 'prepare'),
                                    'ready'), 'deliver')

    def ids(self, query=''):
        response = self.client.get(f'{LIST_URL}?{query}')
        self.assertEqual(response.status_code, 200, response.content)
        return [o['id'] for o in response.json()['results']]

    def test_summary_resource_and_pagination_shape(self):  # AC-16
        body = self.client.get(LIST_URL).json()
        self.assertEqual(set(body), {'count', 'next', 'previous', 'results'})
        self.assertEqual(body['count'], 5)
        self.assertEqual(set(body['results'][0]), SUMMARY_KEYS)
        row = next(r for r in body['results'] if r['id'] == self.o3['id'])
        self.assertEqual((row['total'], row['paid_total'], row['balance'], row['payment_status'], row['status']),
                         ('70.00', '10.00', '60.00', 'PARTIAL', 'NEW'))
        ana_row = next(r for r in body['results'] if r['id'] == self.o1['id'])
        self.assertEqual(ana_row['customer'], {'id': str(self.ana.id), 'name': 'Ana'})
        self.assertIsNone(row['customer'])

    def test_default_order_is_newest_first(self):  # AC-16
        self.assertEqual(self.ids(), [self.o4['id'], self.o3['id'], self.o5['id'], self.o2['id'], self.o1['id']])

    def test_order_by_expected_delivery(self):  # AC-16
        self.assertEqual(self.ids('ordering=expected_delivery_date'),
                         [self.o4['id'], self.o2['id'], self.o1['id'], self.o5['id'], self.o3['id']])

    def test_pending_deliveries_shortcut(self):  # AC-16
        ids = self.ids('status=NEW,IN_PREPARATION,READY&ordering=expected_delivery_date')
        self.assertEqual(ids, [self.o2['id'], self.o1['id'], self.o3['id']])

    def test_delivered_and_cancelled_shortcuts(self):  # AC-16
        self.assertEqual(self.ids('status=DELIVERED'), [self.o5['id']])
        self.assertEqual(self.ids('status=CANCELLED'), [self.o4['id']])

    def test_receivable_shortcut(self):  # AC-16
        ids = self.ids('has_balance=true&status=NEW,IN_PREPARATION,READY,DELIVERED')
        self.assertEqual(set(ids), {self.o1['id'], self.o3['id'], self.o5['id']})
        self.assertEqual(self.ids('has_balance=false'), [self.o2['id']])

    def test_payment_status_filter(self):  # AC-16
        self.assertEqual(self.ids('payment_status=PAID'), [self.o2['id']])
        self.assertEqual(set(self.ids('payment_status=PENDING,PARTIAL')),
                         {self.o1['id'], self.o3['id'], self.o4['id'], self.o5['id']})

    def test_channel_and_customer_filters(self):  # AC-08, AC-16
        self.assertEqual(self.ids('sales_channel=STORE'), [self.o2['id']])
        self.assertEqual(self.ids(f'customer_id={self.ana.id}'), [self.o5['id'], self.o1['id']])
        self.assertEqual(self.ids(f'customer_id={uuid4()}'), [])  # EDGE-09

    def test_orders_of_an_inactive_customer_are_still_listed(self):  # AC-16, EDGE-08
        own = self.order_with_item(customer_id=str(self.ana.id))
        CustomerModel.objects.filter(pk=self.ana.id).update(active=False)
        self.assertIn(own['id'], self.ids(f'customer_id={self.ana.id}'))
        row = next(r for r in self.client.get(f'{LIST_URL}?customer_id={self.ana.id}').json()['results']
                   if r['id'] == own['id'])
        self.assertEqual(row['customer']['name'], 'Ana')

    def test_date_ranges(self):  # AC-10, AC-16
        self.assertEqual(self.ids('date_from=2026-10-03&date_to=2026-10-05'),
                         [self.o3['id'], self.o5['id'], self.o2['id']])
        self.assertEqual(self.ids('date_field=expected_delivery_date&date_from=2026-10-09&date_to=2026-10-12'
                                  '&ordering=expected_delivery_date'), [self.o2['id'], self.o1['id']])
        self.assertEqual(self.ids('date_from=2026-10-20'), [])

    def test_invalid_parameters(self):  # AC-16, EDGE-10
        cases = {
            'status=NEW,FOO': 'status', 'payment_status=X': 'payment_status', 'sales_channel=X': 'sales_channel',
            'customer_id=abc': 'customer_id', 'date_from=ayer': 'date_from', 'date_field=created': 'date_field',
            'has_balance=maybe': 'has_balance', 'ordering=total': 'ordering',
            'date_from=2026-10-09&date_to=2026-10-01': 'date_to',
        }
        for query, param in cases.items():
            response = self.client.get(f'{LIST_URL}?{query}')
            self.assertEqual(response.status_code, 400, query)
            self.assertIn(param, response.json(), query)

    def test_pagination_size_and_cap(self):  # AC-16
        body = self.client.get(f'{LIST_URL}?page_size=2').json()
        self.assertEqual((len(body['results']), body['count'], bool(body['next'])), (2, 5, True))
        self.assertEqual(len(self.client.get(f'{LIST_URL}?page_size=500').json()['results']), 5)
        self.assertEqual(self.client.get(f'{LIST_URL}?page=9').status_code, 404)

    def test_list_does_not_query_per_row(self):  # NFR rendimiento
        with self.assertNumQueries(4):  # token con usuario + count + filas + nombres de cliente
            self.client.get(LIST_URL)
