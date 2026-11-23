"""TASK-pedido-pantalla-unica-creacion: `POST /api/orders/start/` crea el pedido completo ya en preparación."""
from decimal import Decimal

from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.catalog.infrastructure.django.models import ProductModel
from modules.customers.infrastructure.django.models import CustomerModel
from modules.inventory.tests.policy import set_negative_stock
from modules.inventory.tests.test_movements import make_warehouse
from modules.modularity.tests.test_enforcement import set_enabled
from modules.sales.infrastructure.django.models import OrderModel
from modules.sales.tests.test_delivery_inventory import ENABLED, DeliveryTestCase, url

START = '/api/orders/start/'


class PlaceOrderTests(DeliveryTestCase):
    def service(self, name='Instalación', price='50.00'):
        return ProductModel.objects.create(company_id=self.company.id, name=name, sale_price=Decimal(price))

    def start(self, items=None, expected_status=201, **extra):
        body = {'sales_channel': 'WHATSAPP', 'warehouse_id': str(self.warehouse.id), **extra}
        if items is None:
            items = [(self.bags, 2)]
        body['items'] = [{'product_id': str(p.id), 'quantity': q} for p, q in items]
        response = self.client.post(START, body, format='json')
        self.assertEqual(response.status_code, expected_status, response.content)
        return response.json()

    def test_creates_the_whole_order_in_preparation(self):  # AC-05
        self.stock(self.bags, 5)
        customer = CustomerModel.objects.create(company_id=self.company.id, name='Ana Pérez')
        body = self.start([(self.bags, 2), (self.service(), 1)], discount='5.00', customer_id=str(customer.id),
                          notes='Entregar por la tarde')
        self.assertEqual((body['status'], body['editable']), ('IN_PREPARATION', True))
        self.assertEqual(body['allowed_transitions'], ['ready', 'cancel'])
        self.assertEqual((body['subtotal'], body['discount'], body['total']), ('70.00', '5.00', '65.00'))
        self.assertEqual([(i['product_name'], i['unit_price'], i['quantity']) for i in body['items']],
                         [('Bolsas', '10.00', 2), ('Instalación', '50.00', 1)])
        self.assertEqual((body['customer']['name'], body['notes']), ('Ana Pérez', 'Entregar por la tarde'))
        self.assertEqual(body['warehouse'], {'id': str(self.warehouse.id), 'name': 'Central'})
        self.assertEqual(self.get(body)['warehouse']['name'], 'Central')

    def test_a_pure_service_order_needs_no_warehouse(self):  # AC-09
        body = self.start([(self.service(), 1)], warehouse_id=None)
        self.assertEqual((body['status'], body['warehouse']), ('IN_PREPARATION', None))

    def test_requires_at_least_one_product(self):  # AC-05
        response = self.client.post(START, {'sales_channel': 'WHATSAPP', 'items': []}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('items', response.json())
        self.assertEqual(OrderModel.objects.count(), 0)

    def test_item_problems_are_reported_by_line_and_nothing_is_saved(self):  # AC-05
        inactive = ProductModel.objects.create(company_id=self.company.id, name='Viejo', sale_price=Decimal('1'),
                                               active=False)
        body = self.start([(self.bags, 1), (inactive, 1), (self.bags, 1)], expected_status=400)
        self.assertEqual(len(body['items']), 2)
        self.assertTrue(body['items'][0].startswith('Línea 2:') and 'inactivo' in body['items'][0])
        self.assertTrue(body['items'][1].startswith('Línea 3:') and 'repetido' in body['items'][1])
        self.assertEqual(OrderModel.objects.count(), 0)

    def test_header_and_item_errors_are_reported_together(self):  # AC-05
        response = self.client.post(START, {'sales_channel': '', 'items': []}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'sales_channel', 'items'})

    def test_discount_above_the_configured_maximum_is_rejected(self):  # AC-04
        self.client.patch('/api/settings/sales/', {'settings': {'sales.max_discount_percent': '10'}}, format='json')
        self.stock(self.bags, 5)
        body = self.start([(self.bags, 2)], discount='5.00', expected_status=400)  # 25 % de 20,00
        self.assertIn('discount', body)
        self.assertEqual(OrderModel.objects.count(), 0)
        self.assertEqual(self.start([(self.bags, 2)], discount='2.00')['discount'], '2.00')

    def test_inactive_customer_is_rejected(self):
        customer = CustomerModel.objects.create(company_id=self.company.id, name='Baja', active=False)
        self.stock(self.bags, 5)
        self.assertIn('customer_id', self.start(customer_id=str(customer.id), expected_status=400))

    def test_missing_warehouse_is_rejected_when_a_product_controls_stock(self):  # INV-04
        body = self.start(warehouse_id=None, expected_status=400)
        self.assertIn('warehouse_id', body)
        self.assertEqual(OrderModel.objects.count(), 0)

    def test_unknown_or_inactive_warehouse_is_rejected(self):  # INV-04, AC-10
        other = make_warehouse(make_company('Empresa B'), 'Ajeno')
        self.stock(self.bags, 5)
        self.assertIn('warehouse_id', self.start(warehouse_id=str(other.id), expected_status=400))
        self.warehouse.active = False
        self.warehouse.save()
        self.assertIn('warehouse_id', self.start(expected_status=400))

    def test_insufficient_stock_rejects_everything(self):  # AC-06, INV-05, INV-06
        self.stock(self.bags, 1)
        body = self.start([(self.bags, 4)], expected_status=409)
        self.assertEqual(body['code'], 'insufficient_stock')
        self.assertEqual(body['warehouse']['name'], 'Central')
        self.assertEqual([(ln['product']['name'], ln['requested'], ln['available']) for ln in body['lines']],
                         [('Bolsas', '4.0000', '1.0000')])
        self.assertEqual(OrderModel.objects.count(), 0)

    def test_stock_is_validated_not_reserved(self):  # INV-05
        self.stock(self.bags, 5)
        first, second = self.start([(self.bags, 4)]), self.start([(self.bags, 4)])
        self.assertEqual(self.balance(self.bags), Decimal('5'))
        self.assertEqual(self.exits().count(), 0)
        self.client.post(url(first, 'ready/'), {}, format='json')
        self.deliver(first)
        self.client.post(url(second, 'ready/'), {}, format='json')
        self.deliver(second, expected_status=409)  # la entrega vuelve a validar

    def test_negative_stock_policy_lets_the_order_start(self):  # INV-05
        set_negative_stock(self.company, True)
        self.assertEqual(self.start([(self.bags, 4)])['status'], 'IN_PREPARATION')

    def test_delivery_uses_the_saved_warehouse_by_default(self):  # AC-07
        other = make_warehouse(self.company, 'Secundario')
        self.stock(self.bags, 5, warehouse=other)
        order = self.start([(self.bags, 3)], warehouse_id=str(other.id))
        self.client.post(url(order, 'ready/'), {}, format='json')
        preview = self.client.get(url(order, 'delivery-preview/')).json()
        self.assertEqual(preview['warehouse_id'], str(other.id))
        delivered = self.client.post(url(order, 'deliver/'), {}, format='json')
        self.assertEqual(delivered.status_code, 200, delivered.content)
        self.assertEqual(self.balance(self.bags, other), Decimal('2'))
        self.assertEqual(delivered.json()['stock_output']['warehouse']['name'], 'Secundario')

    def test_the_delivery_dialog_can_still_choose_another_warehouse(self):  # AC-07
        other = make_warehouse(self.company, 'Secundario')
        self.stock(self.bags, 5)
        self.stock(self.bags, 5, warehouse=other)
        order = self.start([(self.bags, 3)])
        self.client.post(url(order, 'ready/'), {}, format='json')
        self.deliver(order, warehouse=other)
        self.assertEqual((self.balance(self.bags), self.balance(self.bags, other)), (Decimal('5'), Decimal('2')))

    def test_inventory_disabled_ignores_the_warehouse(self):  # AC-09
        set_enabled(self.company, tuple(k for k in ENABLED if k != 'inventory'))
        body = self.start([(self.bags, 2)])
        self.assertEqual((body['status'], body['warehouse']), ('IN_PREPARATION', None))

    def test_existing_flow_is_untouched(self):  # AC-08
        created = self.client.post('/api/orders/', {'sales_channel': 'WHATSAPP'}, format='json').json()
        self.assertEqual((created['status'], created['warehouse']), ('NEW', None))
        self.assertEqual(created['allowed_transitions'], ['prepare', 'cancel'])


class PlaceOrderIsolationTests(APITestCase):
    def test_products_of_another_company_are_not_accepted(self):  # AC-10
        mine, theirs = make_company('Empresa A'), make_company('Empresa B')
        authenticate(self.client, make_admin(mine, username='ana'))
        foreign = ProductModel.objects.create(company_id=theirs.id, name='Ajeno', sale_price=Decimal('9'))
        response = self.client.post(
            START, {'sales_channel': 'WHATSAPP', 'items': [{'product_id': str(foreign.id), 'quantity': 1}]},
            format='json')
        self.assertEqual(response.status_code, 400, response.content)
        self.assertTrue(response.json()['items'][0].startswith('Línea 1:'))
        self.assertEqual(OrderModel.objects.count(), 0)

    def test_requires_authentication(self):
        self.assertEqual(self.client.post(START, {}, format='json').status_code, 401)
