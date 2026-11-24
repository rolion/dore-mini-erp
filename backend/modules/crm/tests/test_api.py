from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.customers.infrastructure.django.models import CustomerModel
from modules.inventory.infrastructure.django.models import WarehouseModel
from modules.sales.domain.order import Order
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository

URL = '/api/crm/customers/'
TODAY = date(2026, 11, 20)


class CrmApiTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))

    def customer(self, name, phone='', active=True, company=None):
        return CustomerModel.objects.create(
            company_id=(company or self.company).id, name=name, phone=phone, active=active)

    def order(self, customer, total='50.00', paid=None, on=date(2026, 11, 1), warehouse=None,
              company=None):
        company = company or self.company
        order = Order.create(sales_channel='WHATSAPP', order_date=on, customer_id=customer.id)
        order.add_item(uuid4(), 'Pack', Decimal(total), 1)
        if paid:
            order.register_payment(Decimal(paid), 'CASH', on, '', TODAY)
        if warehouse is not None:
            order.assign_warehouse(warehouse.id)
        return DjangoOrderRepository(company.id).save(order)

    def warehouse(self, name='Central', company=None):
        return WarehouseModel.objects.create(company_id=(company or self.company).id, name=name)

    def enable_inventory(self):
        self.assertEqual(self.client.post('/api/modules/inventory/enable/').status_code, 200)

    def names(self, **params):
        response = self.client.get(URL, params)
        self.assertEqual(response.status_code, 200, response.content)
        return [r['display_name'] for r in response.json()['results']]


class FieldsTests(CrmApiTestCase):
    def test_row_fields_with_and_without_orders(self):  # AC-05
        ana = self.customer('Ana', '+59176543210')
        self.customer('Beto')
        self.order(ana, total='50.00', paid='20.00', on=date(2026, 11, 1))
        self.order(ana, total='30.00', paid='30.00', on=date(2026, 11, 10))
        body = self.client.get(URL).json()
        first, second = body['results']
        self.assertEqual(set(first), {'customer_id', 'display_name', 'phone', 'last_purchase_at', 'order_count',
                                      'outstanding_amount', 'currency'})
        self.assertEqual((first['display_name'], first['phone'], first['order_count']), ('Ana', '+59176543210', 2))
        self.assertEqual((first['last_purchase_at'], first['outstanding_amount'], first['currency']),
                         ('2026-11-10', '30.00', 'BOB'))
        self.assertEqual((second['last_purchase_at'], second['order_count'], second['outstanding_amount']),
                         (None, 0, '0.00'))
        self.assertEqual(body['meta'], {'sales_enabled': True, 'warehouse_filter_enabled': False})

    def test_inactive_customers_are_excluded(self):  # INV-03
        self.customer('Ana')
        self.customer('Zeta', active=False)
        self.assertEqual(self.names(), ['Ana'])

    def test_works_without_any_segment(self):  # AC-08, INV-04
        self.customer('Ana')
        self.assertEqual(self.client.get(URL).json()['count'], 1)

    def test_customer_without_phone_returns_empty_string(self):  # AC-05
        self.customer('Sin teléfono')
        self.assertEqual(self.client.get(URL).json()['results'][0]['phone'], '')

    def test_empty_state(self):  # AC-07
        body = self.client.get(URL).json()
        self.assertEqual((body['count'], body['results']), (0, []))


class SearchAndPaginationTests(CrmApiTestCase):
    def test_search_by_name_and_phone(self):  # AC-01
        self.customer('Ana Pérez', '+59176543210')
        self.customer('Beto Luna', '+59170001111')
        self.assertEqual(self.names(search='pér'), ['Ana Pérez'])
        self.assertEqual(self.names(search='7000'), ['Beto Luna'])
        self.assertEqual(self.names(search='  '), ['Ana Pérez', 'Beto Luna'])

    def test_ties_on_name_keep_a_stable_order_across_pages(self):  # AC-03
        for _ in range(4):
            self.customer('Igual')
        first = [r['customer_id'] for r in self.client.get(URL, {'page_size': 2, 'page': 1}).json()['results']]
        second = [r['customer_id'] for r in self.client.get(URL, {'page_size': 2, 'page': 2}).json()['results']]
        self.assertEqual(len(set(first + second)), 4)
        self.assertEqual(first + second, sorted(first + second, key=lambda i: i))

    def test_pagination_and_stable_order(self):  # AC-03
        for index in range(5):
            self.customer(f'Cliente {index}')
        page = self.client.get(URL, {'page_size': 2, 'page': 2}).json()
        self.assertEqual(page['count'], 5)
        self.assertEqual([r['display_name'] for r in page['results']], ['Cliente 2', 'Cliente 3'])
        self.assertIsNotNone(page['next'])
        self.assertEqual(self.client.get(URL, {'page': 9}).status_code, 404)


class WarehouseFilterTests(CrmApiTestCase):
    def setUp(self):
        super().setUp()
        self.enable_inventory()
        self.central, self.norte = self.warehouse('Central'), self.warehouse('Norte')
        self.ana, self.beto, self.carla = self.customer('Ana'), self.customer('Beto'), self.customer('Carla')
        self.order(self.ana, warehouse=self.central)
        self.order(self.ana, warehouse=self.norte, total='10.00')
        self.order(self.beto, warehouse=self.norte)
        self.order(self.carla)  # histórico sin almacén

    def test_filter_returns_customers_with_orders_in_warehouse(self):  # AC-02
        self.assertEqual(self.names(warehouse_id=self.central.id), ['Ana'])
        self.assertEqual(self.names(warehouse_id=self.norte.id), ['Ana', 'Beto'])

    def test_aggregates_are_not_narrowed_by_the_filter(self):  # INV-02
        row = self.client.get(URL, {'warehouse_id': self.central.id}).json()['results'][0]
        self.assertEqual((row['order_count'], row['outstanding_amount']), (2, '60.00'))

    def test_inactive_warehouse_is_not_a_valid_branch(self):  # AC-02 (sucursal = almacén activo)
        retired = WarehouseModel.objects.create(company_id=self.company.id, name='Cerrada', active=False)
        response = self.client.get(URL, {'warehouse_id': retired.id})
        self.assertEqual(response.status_code, 400)

    def test_meta_enables_filter(self):  # AC-09
        self.assertTrue(self.client.get(URL).json()['meta']['warehouse_filter_enabled'])

    def test_invalid_or_foreign_warehouse_is_rejected(self):  # AC-02, AC-04
        other = make_company('Empresa B')
        foreign = self.warehouse('Ajeno', company=other)
        for value in (uuid4(), foreign.id, 'no-es-uuid'):
            response = self.client.get(URL, {'warehouse_id': value})
            self.assertEqual(response.status_code, 400, value)
            self.assertIn('warehouse_id', response.json())

    def test_filter_rejected_when_inventory_disabled(self):  # AC-09
        self.client.post('/api/modules/inventory/disable/')
        response = self.client.get(URL, {'warehouse_id': self.central.id})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.client.get(URL).json()['meta']['warehouse_filter_enabled'])


class ModuleAndIsolationTests(CrmApiTestCase):
    def test_company_isolation(self):  # AC-04, INV-01
        other = make_company('Empresa B')
        mine, theirs = self.customer('Mia'), self.customer('Ajeno', company=other)
        self.order(mine)
        self.order(theirs, company=other, total='999.00')
        body = self.client.get(URL).json()
        self.assertEqual([r['display_name'] for r in body['results']], ['Mia'])
        self.assertEqual(body['results'][0]['outstanding_amount'], '50.00')

    def test_orders_of_other_company_never_aggregate(self):  # AC-04
        other = make_company('Empresa B')
        self.customer('Mia')
        theirs = CustomerModel.objects.create(company_id=other.id, name='X')
        self.order(theirs, company=other)
        self.assertEqual(self.client.get(URL).json()['results'][0]['order_count'], 0)

    def test_requires_authentication_and_customers_module(self):  # AC-06
        self.client.credentials()
        self.assertIn(self.client.get(URL).status_code, (401, 403))

    def test_user_without_company_is_forbidden(self):  # AC-04
        loner = get_user_model().objects.create_superuser(username='sin-empresa', password='x-Pass-123')
        authenticate(self.client, loner)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_customers_module_disabled_blocks_api(self):
        self.client.post('/api/modules/sales/disable/')
        self.client.post('/api/modules/reporting/disable/')
        self.client.post('/api/modules/customers/disable/')
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_without_sales_there_are_no_aggregates(self):  # AC-09
        ana = self.customer('Ana')
        self.order(ana)
        self.client.post('/api/modules/sales/disable/')
        body = self.client.get(URL).json()
        self.assertFalse(body['meta']['sales_enabled'])
        self.assertEqual((body['results'][0]['order_count'], body['results'][0]['outstanding_amount']), (0, '0.00'))
