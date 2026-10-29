"""PB-INT-002: entregar un pedido registra la salida de inventario de sus productos controlados."""
from decimal import Decimal
from threading import Barrier, Thread
from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient, APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.inventory import services as inventory
from modules.inventory.infrastructure.django.models import StockMovementModel, WarehouseModel
from modules.inventory.tests.policy import set_negative_stock
from modules.inventory.tests.test_movements import make_product, make_warehouse
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled

ENABLED = DEFAULT_ENABLED_KEYS + ('inventory',)


def url(order, suffix=''):
    return f'/api/orders/{order["id"]}/{suffix}'


class DeliveryTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.user = make_admin(self.company, username='ana')
        authenticate(self.client, self.user)
        set_enabled(self.company, ENABLED)
        self.warehouse = make_warehouse(self.company, 'Central')
        self.bags = make_product(self.company, 'Bolsas', allows_fractions=False, abbreviation='u')

    # --- fixtures
    def stock(self, product, quantity, warehouse=None):
        inventory.record_movement(
            self.company.id, product_id=product.id, warehouse_id=(warehouse or self.warehouse).id, kind='in',
            quantity=Decimal(quantity), user_id=None, user_name='ana')

    def balance(self, product, warehouse=None):
        return inventory.get_balance(self.company.id, product.id, (warehouse or self.warehouse).id)

    def order(self, *items, ready=True, client=None):
        client = client or self.client
        created = client.post('/api/orders/', {'sales_channel': 'WHATSAPP'}, format='json').json()
        for product, quantity in items:
            response = client.post(url(created, 'items/'), {'product_id': str(product.id), 'quantity': quantity},
                                   format='json')
            self.assertEqual(response.status_code, 201, response.content)
        if ready:
            for action in ('prepare', 'ready'):
                self.assertEqual(client.post(url(created, f'{action}/'), {}, format='json').status_code, 200)
        return created

    def deliver(self, order, warehouse=None, expected_status=200, **extra):
        body = dict(extra)
        warehouse = self.warehouse if warehouse is None else warehouse
        if warehouse is not False:
            body['warehouse_id'] = str(warehouse.id)
        response = self.client.post(url(order, 'deliver/'), body, format='json')
        self.assertEqual(response.status_code, expected_status, response.content)
        return response.json()

    def get(self, order):
        return self.client.get(url(order)).json()

    def exits(self, **filters):
        return StockMovementModel.objects.filter(company_id=self.company.id, kind='out', **filters)


class DeliverWithStockTests(DeliveryTestCase):
    def test_delivery_creates_the_exit_and_leaves_the_balance(self):  # AC-01, AC-10, AC-12
        self.stock(self.bags, 5)
        order = self.order((self.bags, 4))
        body = self.deliver(order)
        self.assertEqual(body['status'], 'DELIVERED')
        self.assertEqual(self.balance(self.bags), Decimal('1'))
        movement = self.exits().get()
        self.assertEqual((movement.quantity, movement.source_type, movement.source_id, movement.source_line,
                          movement.reference, movement.user_name, movement.warehouse_id),
                         (Decimal('4'), 'sales_order', order['id'], str(self.bags.id), order['code'], 'ana',
                          self.warehouse.id))
        output = body['stock_output']
        self.assertEqual((output['reference'], output['warehouse']['name'], output['user_name']),
                         (order['code'], 'Central', 'ana'))
        self.assertEqual(
            [(m['product']['name'], m['quantity'], m['unit']['abbreviation']) for m in output['movements']],
            [('Bolsas', '4.0000', 'u')])
        self.assertEqual(self.get(order)['stock_output'], output)

    def test_earlier_steps_never_touch_the_stock(self):  # AC-09, INV-01
        self.stock(self.bags, 5)
        order = self.order((self.bags, 4), ready=False)
        for action in ('prepare', 'ready'):
            self.assertEqual(self.client.post(url(order, f'{action}/'), {}, format='json').status_code, 200)
        self.client.post(url(order, 'payments/'), {'amount': '40.00', 'payment_method': 'CASH'}, format='json')
        self.assertEqual(self.get(order)['payment_status'], 'PAID')
        self.assertEqual(self.get(order)['status'], 'READY')
        self.assertEqual((self.balance(self.bags), self.exits().count()), (Decimal('5'), 0))
        self.assertIsNone(self.get(order)['stock_output'])

    def test_blocked_policy_rejects_the_second_delivery_and_keeps_it_ready(self):  # AC-02
        self.stock(self.bags, 5)
        first, second = self.order((self.bags, 4)), self.order((self.bags, 4))
        self.deliver(first)
        response = self.client.post(url(second, 'deliver/'), {'warehouse_id': str(self.warehouse.id)}, format='json')
        self.assertEqual(response.status_code, 409, response.content)
        body = response.json()
        self.assertEqual(body['code'], 'insufficient_stock')
        self.assertEqual(body['warehouse']['name'], 'Central')
        self.assertEqual(
            [(ln['product']['name'], ln['unit']['abbreviation'], ln['requested'], ln['available'])
             for ln in body['lines']], [('Bolsas', 'u', '4.0000', '1.0000')])
        self.assertEqual(self.get(second)['status'], 'READY')
        self.assertIsNone(self.get(second)['stock_output'])
        self.assertEqual((self.exits().count(), self.balance(self.bags)), (1, Decimal('1')))

    def test_allowed_policy_lets_both_deliveries_go_negative(self):  # AC-03
        set_negative_stock(self.company, True)
        self.stock(self.bags, 5)
        first, second = self.order((self.bags, 4)), self.order((self.bags, 4))
        self.deliver(first)
        self.deliver(second)
        self.assertEqual(self.balance(self.bags), Decimal('-3'))
        for order in (first, second):
            self.assertEqual(self.exits(source_id=order['id']).count(), 1)
            self.assertEqual(len(self.get(order)['stock_output']['movements']), 1)

    def test_repeating_the_delivery_does_not_discount_twice(self):  # AC-04
        self.stock(self.bags, 5)
        order = self.order((self.bags, 2))
        self.deliver(order)
        response = self.client.post(url(order, 'deliver/'), {'warehouse_id': str(self.warehouse.id)}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'invalid_transition')
        self.assertEqual((self.exits().count(), self.balance(self.bags)), (1, Decimal('3')))

    def test_a_short_line_confirms_nothing(self):  # AC-05
        other = make_product(self.company, 'Cajas', allows_fractions=False, abbreviation='u')
        self.stock(self.bags, 10)
        self.stock(other, 1)
        order = self.order((self.bags, 3), (other, 5))
        response = self.client.post(url(order, 'deliver/'), {'warehouse_id': str(self.warehouse.id)}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual([ln['product']['name'] for ln in response.json()['lines']], ['Cajas'])
        self.assertEqual(self.get(order)['status'], 'READY')
        self.assertEqual((self.exits().count(), self.balance(self.bags)), (0, Decimal('10')))

    def test_every_short_line_is_reported(self):  # AC-05
        other = make_product(self.company, 'Cajas', allows_fractions=False, abbreviation='u')
        order = self.order((self.bags, 3), (other, 5))
        response = self.client.post(url(order, 'deliver/'), {'warehouse_id': str(self.warehouse.id)}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(sorted(ln['product']['name'] for ln in response.json()['lines']), ['Bolsas', 'Cajas'])

    def test_only_controlled_products_generate_exits(self):  # AC-06
        free = make_product(self.company, 'Servicio', tracks_stock=False)
        self.stock(self.bags, 5)
        order = self.order((self.bags, 2), (free, 3))
        self.deliver(order)
        self.assertEqual([m.product_id for m in self.exits()], [self.bags.id])

    def test_order_without_controlled_products_needs_no_warehouse(self):  # AC-06
        free = make_product(self.company, 'Servicio', tracks_stock=False)
        order = self.order((free, 3))
        body = self.deliver(order, warehouse=False)
        self.assertEqual((body['status'], body['stock_output']), ('DELIVERED', None))
        self.assertEqual(self.exits().count(), 0)

    def test_delivered_order_cannot_be_edited_or_cancelled(self):  # AC-13, INV-07
        self.stock(self.bags, 5)
        order = self.order((self.bags, 2))
        body = self.deliver(order)
        item = body['items'][0]
        self.assertEqual(
            self.client.patch(url(order, f'items/{item["id"]}/'), {'quantity': 1}, format='json').status_code, 409)
        self.assertEqual(self.client.post(url(order, 'cancel/'), {'reason': 'x'}, format='json').status_code, 409)
        self.assertEqual(self.balance(self.bags), Decimal('3'))


class WarehouseRulesTests(DeliveryTestCase):
    def test_warehouse_is_required_when_there_are_controlled_items(self):  # AC-07
        self.stock(self.bags, 5)
        order = self.order((self.bags, 2))
        response = self.client.post(url(order, 'deliver/'), {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('warehouse_id', response.json())
        self.assertEqual((self.get(order)['status'], self.exits().count()), ('READY', 0))

    def test_foreign_or_unknown_warehouse_is_rejected(self):  # AC-07, AC-15
        self.stock(self.bags, 5)
        order = self.order((self.bags, 2))
        foreign = make_warehouse(make_company('Empresa B'), 'Ajeno')
        for warehouse in (foreign, WarehouseModel(id='11111111-1111-1111-1111-111111111111')):
            response = self.client.post(url(order, 'deliver/'), {'warehouse_id': str(warehouse.id)}, format='json')
            self.assertEqual(response.status_code, 400, response.content)
            self.assertIn('warehouse_id', response.json())
        self.assertEqual((self.get(order)['status'], self.exits().count()), ('READY', 0))

    def test_inactive_warehouse_is_rejected(self):  # AC-07
        self.stock(self.bags, 5)
        spare = make_warehouse(self.company, 'Secundario')
        order = self.order((self.bags, 2))
        spare.active = False
        spare.save()
        response = self.client.post(url(order, 'deliver/'), {'warehouse_id': str(spare.id)}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get(order)['status'], 'READY')

    def test_company_without_an_active_warehouse_cannot_deliver_controlled_items(self):  # AC-07
        order = self.order((self.bags, 2))
        WarehouseModel.objects.filter(company_id=self.company.id).update(active=False)
        response = self.client.post(url(order, 'deliver/'), {'warehouse_id': str(self.warehouse.id)}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'no_active_warehouse')
        self.assertEqual(self.get(order)['status'], 'READY')


class InventoryDisabledTests(DeliveryTestCase):
    def test_delivery_works_as_before_and_is_not_retroactive(self):  # AC-08
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)
        self.stock(self.bags, 5)
        order = self.order((self.bags, 4))
        body = self.deliver(order, warehouse=False)
        self.assertEqual((body['status'], body['stock_output']), ('DELIVERED', None))
        set_enabled(self.company, ENABLED)
        self.assertIsNone(self.get(order)['stock_output'])
        self.assertEqual((self.balance(self.bags), self.exits().count()), (Decimal('5'), 0))


class DeliveryPreviewTests(DeliveryTestCase):
    def preview(self, order, expected_status=200, **query):
        response = self.client.get(url(order, 'delivery-preview/'), query)
        self.assertEqual(response.status_code, expected_status, response.content)
        return response.json()

    def test_preview_lists_lines_balances_and_policy_without_writing(self):  # AC-11, AC-10
        self.stock(self.bags, 5)
        order = self.order((self.bags, 4))
        before = StockMovementModel.objects.count()
        body = self.preview(order)
        self.assertEqual(
            (body['inventory_enabled'], body['requires_stock_output'], body['allow_negative_stock']),
            (True, True, False))
        self.assertEqual(body['warehouse_id'], str(self.warehouse.id))
        self.assertEqual([w['name'] for w in body['warehouses']], ['Central'])
        self.assertEqual(body['lines'], [{
            'product': {'id': str(self.bags.id), 'name': 'Bolsas'}, 'quantity': '4.0000',
            'unit': {'abbreviation': 'u'}, 'available': '5.0000', 'projected': '1.0000', 'insufficient': False}])
        self.assertEqual(StockMovementModel.objects.count(), before)

    def test_preview_flags_shortage_and_negative_policy(self):  # AC-11
        self.stock(self.bags, 1)
        order = self.order((self.bags, 4))
        line = self.preview(order)['lines'][0]
        self.assertEqual((line['projected'], line['insufficient']), ('-3.0000', True))
        set_negative_stock(self.company, True)
        self.assertTrue(self.preview(order)['allow_negative_stock'])

    def test_with_several_warehouses_the_default_is_suggested_and_a_choice_is_honoured(self):  # AC-11
        self.stock(self.bags, 5)
        other = make_warehouse(self.company, 'Zona')
        other.is_default = True
        other.save()
        WarehouseModel.objects.filter(pk=self.warehouse.pk).update(is_default=False)
        order = self.order((self.bags, 2))
        self.assertEqual(self.preview(order)['warehouse_id'], str(other.id))
        chosen = self.preview(order, warehouse_id=str(self.warehouse.id))
        self.assertEqual((chosen['warehouse_id'], chosen['lines'][0]['available']),
                         (str(self.warehouse.id), '5.0000'))

    def test_preview_without_controlled_items_or_inventory(self):  # AC-06, AC-08
        free = make_product(self.company, 'Servicio', tracks_stock=False)
        order = self.order((free, 1))
        body = self.preview(order)
        self.assertEqual((body['inventory_enabled'], body['requires_stock_output'], body['lines']),
                         (True, False, []))
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)
        self.assertEqual(self.preview(order)['inventory_enabled'], False)

    def test_preview_writes_nothing_even_without_warehouses(self):  # AC-11, REV-01
        order = self.order((self.bags, 1))
        WarehouseModel.objects.filter(company_id=self.company.id).delete()
        body = self.preview(order)
        self.assertEqual((body['warehouses'], body['warehouse_id']), ([], None))
        self.assertEqual(WarehouseModel.objects.filter(company_id=self.company.id).count(), 0)

    def test_preview_requires_a_ready_order_of_the_company(self):  # AC-11, AC-15
        draft = self.order((self.bags, 1), ready=False)
        self.assertEqual(self.preview(draft, expected_status=409)['code'], 'invalid_transition')
        ready = self.order((self.bags, 1))
        foreign = make_warehouse(make_company('Empresa B'), 'Ajeno')
        self.preview(ready, expected_status=400, warehouse_id=str(foreign.id))
        other_client = APIClient()
        authenticate(other_client, make_admin(make_company('Empresa C'), username='luis'))
        response = other_client.get(url(ready, 'delivery-preview/'))
        self.assertEqual(response.status_code, 404)
        response = other_client.post(url(ready, 'deliver/'), {'warehouse_id': str(self.warehouse.id)}, format='json')
        self.assertEqual(response.status_code, 404)


class TwoCompaniesTests(DeliveryTestCase):
    def test_same_names_in_two_companies_never_mix_stock_or_movements(self):  # AC-15, REV-02
        other_company = make_company('Empresa B')
        other_client = APIClient()
        authenticate(other_client, make_admin(other_company, username='luis'))
        set_enabled(other_company, ENABLED)
        other_warehouse = make_warehouse(other_company, 'Central')  # mismo nombre que el de la empresa A
        other_bags = make_product(other_company, 'Bolsas', allows_fractions=False, abbreviation='u')
        inventory.record_movement(
            other_company.id, product_id=other_bags.id, warehouse_id=other_warehouse.id, kind='in',
            quantity=Decimal('5'), user_id=None, user_name='luis')
        self.stock(self.bags, 5)
        mine = self.order((self.bags, 4))
        theirs = self.order((other_bags, 4), client=other_client)
        self.deliver(mine)
        # La entrega de A no tocó el saldo de B ni sus movimientos.
        self.assertEqual(inventory.get_balance(other_company.id, other_bags.id, other_warehouse.id), Decimal('5'))
        self.assertEqual(StockMovementModel.objects.filter(company_id=other_company.id, kind='out').count(), 0)
        self.assertEqual(self.balance(self.bags), Decimal('1'))
        # La empresa B entrega la suya con su propio almacén homónimo: su saldo baja y el de A no cambia.
        response = other_client.post(
            url(theirs, 'deliver/'), {'warehouse_id': str(other_warehouse.id)}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(inventory.get_balance(other_company.id, other_bags.id, other_warehouse.id), Decimal('1'))
        self.assertEqual(self.balance(self.bags), Decimal('1'))
        self.assertEqual(self.exits().count(), 1)
        # Cada empresa ve solo sus movimientos y el almacén de la otra no se acepta aunque se llame igual.
        other_rows = other_client.get('/api/stock-movements/', {'kind': 'out'}).json()['results']
        self.assertEqual([r['source']['id'] for r in other_rows], [theirs['id']])
        another = self.order((self.bags, 1))
        response = self.client.post(url(another, 'deliver/'), {'warehouse_id': str(other_warehouse.id)}, format='json')
        self.assertEqual(response.status_code, 400, response.content)


class MovementsByOrderTests(DeliveryTestCase):
    def test_movements_are_visible_from_inventory_filtered_by_order(self):  # AC-12
        self.stock(self.bags, 10)
        first, second = self.order((self.bags, 2)), self.order((self.bags, 3))
        self.deliver(first)
        self.deliver(second)
        response = self.client.get('/api/stock-movements/', {'source_type': 'sales_order', 'source_id': first['id']})
        self.assertEqual(response.status_code, 200)
        rows = response.json()['results']
        self.assertEqual([(r['quantity_out'], r['reference'], r['source']['id'], r['source']['available'])
                          for r in rows], [('2.0000', first['code'], first['id'], True)])
        detail = self.client.get(f'/api/stock-movements/{rows[0]["id"]}/').json()
        self.assertEqual(detail['user']['name'], 'ana')

    def test_source_id_needs_a_source_type(self):  # AC-12
        response = self.client.get('/api/stock-movements/', {'source_id': 'abc'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('source_id', response.json())


@skipUnless(connection.vendor == 'postgresql', 'La concurrencia real exige PostgreSQL (select_for_update).')
class ConcurrentDeliveryTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('Empresa C')
        self.user = make_admin(self.company, username='ana')
        set_enabled(self.company, ENABLED)
        self.warehouse = make_warehouse(self.company)
        self.bags = make_product(self.company, 'Bolsas', allows_fractions=False, abbreviation='u')
        inventory.record_movement(
            self.company.id, product_id=self.bags.id, warehouse_id=self.warehouse.id, kind='in',
            quantity=Decimal('5'), user_id=None, user_name='ana')

    def api_client(self):
        client = APIClient()
        authenticate(client, self.user)
        return client

    def ready_order(self, quantity):
        client = self.api_client()
        order = client.post('/api/orders/', {'sales_channel': 'WHATSAPP'}, format='json').json()
        client.post(url(order, 'items/'), {'product_id': str(self.bags.id), 'quantity': quantity}, format='json')
        client.post(url(order, 'prepare/'), {}, format='json')
        client.post(url(order, 'ready/'), {}, format='json')
        return order

    def run_threads(self, orders):
        barrier = Barrier(len(orders))
        statuses: list[int] = []

        def target(order):
            client = self.api_client()
            try:
                barrier.wait()
                response = client.post(url(order, 'deliver/'), {'warehouse_id': str(self.warehouse.id)},
                                       format='json')
                statuses.append(response.status_code)
            finally:
                connection.close()

        threads = [Thread(target=target, args=(order,)) for order in orders]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return sorted(statuses)

    def balance(self):
        return inventory.get_balance(self.company.id, self.bags.id, self.warehouse.id)

    def test_two_deliveries_over_the_same_stock_confirm_only_one(self):  # AC-02
        first, second = self.ready_order(4), self.ready_order(4)
        self.assertEqual(self.run_threads([first, second]), [200, 409])
        self.assertEqual(StockMovementModel.objects.filter(kind='out').count(), 1)
        self.assertEqual(self.balance(), Decimal('1'))

    def test_the_same_order_delivered_twice_at_once_discounts_once(self):  # AC-04
        order = self.ready_order(2)
        statuses = self.run_threads([order, order, order])
        self.assertEqual(statuses.count(200), 1)
        self.assertEqual(StockMovementModel.objects.filter(kind='out').count(), 1)
        self.assertEqual(self.balance(), Decimal('3'))
