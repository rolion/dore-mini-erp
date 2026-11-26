from decimal import Decimal
from threading import Barrier, Thread
from uuid import uuid4

from django.db import connection, transaction
from django.test import TransactionTestCase
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.inventory import services as inventory_services
from modules.inventory.infrastructure.django.models import StockLotModel, StockMovementModel, WarehouseModel
from modules.catalog.infrastructure.django.models import ProductModel, UnitModel
from modules.modularity.infrastructure.django.models import CompanyModuleModel, CompanySettingsModel

URL = '/api/production-orders/'


class OrderApiTests(APITestCase):
    def setUp(self):
        self.company = make_company('Producción A')
        self.user = make_admin(self.company, username='prod-admin')
        authenticate(self.client, self.user)
        CompanySettingsModel.objects.create(company_id=self.company.id)
        CompanyModuleModel.objects.create(company_id=self.company.id, module_key='production')
        self.unit = UnitModel.objects.create(company_id=self.company.id, name='Unidad', abbreviation='u')
        self.kilo = UnitModel.objects.create(company_id=self.company.id, name='Kilogramo', abbreviation='kg',
                                             allows_fractions=True)
        self.result = self.product('Cuñapé a granel', self.unit)
        self.cheese = self.product('Queso', self.kilo)
        self.flour = self.product('Almidón', self.kilo)
        self.warehouse = WarehouseModel.objects.create(company_id=self.company.id, name='Central', is_default=True)
        self.recipe = self.create()

    def enable(self, company):
        CompanySettingsModel.objects.get_or_create(company_id=company.id)
        CompanyModuleModel.objects.get_or_create(company_id=company.id, module_key='production')

    def product(self, name, unit):
        return ProductModel.objects.create(company_id=self.company.id, name=name, base_unit=unit,
                                           sale_price=Decimal('1.00'))

    def payload(self, **changes):
        body = {'name': 'Queso', 'result_product_id': str(self.result.id), 'yield_quantity': '24',
                'ingredients': [{'product_id': str(self.cheese.id), 'unit_id': str(self.kilo.id), 'quantity': '1.5'},
                                {'product_id': str(self.flour.id), 'unit_id': str(self.kilo.id), 'quantity': '2'}]}
        body.update(changes)
        return body

    def create(self, **changes):
        response = self.client.post('/api/recipes/', self.payload(**changes), format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def order_payload(self, **changes):
        body = {'recipe_id': self.recipe['id'], 'warehouse_id': str(self.warehouse.id), 'preparations': 5}
        body.update(changes)
        return body

    def make_order(self, **changes):
        response = self.client.post(URL, self.order_payload(**changes), format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_create_computes_expected_values(self):  # AC-01
        body = self.make_order()
        self.assertEqual((body['number'], body['status'], body['preparations']), (1, 'draft', 5))
        self.assertEqual((body['yield_per_preparation'], body['expected_output']), ('24.0000', '120.0000'))
        self.assertEqual([(i['product_name'], i['quantity_per_preparation'], i['expected_quantity'])
                          for i in body['ingredients']],
                         [('Queso', '1.5000', '7.5000'), ('Almidón', '2.0000', '10.0000')])
        self.assertEqual(body['warehouse']['name'], 'Central')
        self.assertIsNone(body['started_at'])
        self.assertEqual(self.client.get(f"{URL}{body['id']}/").json(), body)
        self.assertEqual(self.client.get(URL).json()['results'], [body])
        self.assertEqual(self.make_order()['number'], 2)

    def test_inactive_or_unknown_recipe_is_rejected(self):  # AC-02
        self.client.post(f"/api/recipes/{self.recipe['id']}/deactivate/")
        for recipe_id in (self.recipe['id'], str(uuid4())):
            response = self.client.post(URL, self.order_payload(recipe_id=recipe_id), format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('recipe_id', response.json())

    def test_recipe_of_another_company_is_rejected(self):  # AC-10
        other = make_company('Producción B')
        self.enable(other)
        other_recipe = self.create(name='Ajena')
        authenticate(self.client, make_admin(other, username='otro-2'))
        response = self.client.post(URL, self.order_payload(recipe_id=other_recipe['id']), format='json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_preparations(self):  # AC-03
        for bad in (0, -1, 2.5, 'abc', '', True, None):
            with self.subTest(bad=bad):
                response = self.client.post(URL, self.order_payload(preparations=bad), format='json')
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn('preparations', response.json())
        response = self.client.post(URL, {k: v for k, v in self.order_payload().items() if k != 'preparations'},
                                    format='json')
        self.assertIn('preparations', response.json())

    def test_invalid_warehouse(self):  # AC-08
        other = make_company('Producción C')
        foreign = WarehouseModel.objects.create(company_id=other.id, name='Ajeno')
        spare = WarehouseModel.objects.create(company_id=self.company.id, name='Inactivo', active=False)
        for warehouse_id in (foreign.id, spare.id, uuid4()):
            with self.subTest(warehouse=warehouse_id):
                response = self.client.post(URL, self.order_payload(warehouse_id=str(warehouse_id)), format='json')
                self.assertEqual(response.status_code, 400)
                self.assertIn('warehouse_id', response.json())

    def test_order_keeps_snapshot_after_recipe_changes(self):  # AC-04
        body = self.make_order()
        eggs = self.product('Huevo', self.unit)
        changes = self.payload(name='Otra', yield_quantity='12', ingredients=[
            {'product_id': str(eggs.id), 'unit_id': str(self.unit.id), 'quantity': '3'}])
        edited = self.client.put(f"/api/recipes/{self.recipe['id']}/", changes, format='json')
        self.assertEqual(edited.status_code, 200, edited.content)
        self.assertEqual((edited.json()['name'], edited.json()['yield_quantity']), ('Otra', '12.0000'))
        self.assertEqual(self.client.post(f"/api/recipes/{self.recipe['id']}/deactivate/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/recipes/{self.recipe['id']}/").json()['active'], False)
        self.assertEqual(self.client.get(f"{URL}{body['id']}/").json(), body)

    def stock_snapshot(self):
        return {'balances': {p.id: inventory_services.get_balance(self.company.id, p.id, self.warehouse.id)
                             for p in (self.cheese, self.flour, self.result)},
                'movements': StockMovementModel.objects.count(),
                'lots': StockLotModel.objects.count()}

    def test_draft_edit_and_start_do_not_touch_stock(self):  # AC-05, AC-06, INV-09
        ProductModel.objects.filter(pk=self.cheese.pk).update(tracks_stock=True)
        inventory_services.record_movement(
            self.company.id, product_id=self.cheese.id, warehouse_id=self.warehouse.id, kind='in',
            quantity=Decimal('10'), user_id=self.user.id, user_name='prod-admin', reference='Seed')
        before = self.stock_snapshot()
        self.assertEqual((before['balances'][self.cheese.id], before['movements']), (Decimal('10'), 1))
        body = self.make_order()
        other = WarehouseModel.objects.create(company_id=self.company.id, name='Cocina')
        edited = self.client.put(f"{URL}{body['id']}/", {'warehouse_id': str(other.id), 'preparations': 2},
                                 format='json')
        self.assertEqual(edited.status_code, 200, edited.content)
        self.assertEqual((edited.json()['expected_output'], edited.json()['warehouse']['name']), ('48.0000', 'Cocina'))
        started = self.client.post(f"{URL}{body['id']}/start/")
        self.assertEqual(started.status_code, 200, started.content)
        self.assertEqual(started.json()['status'], 'in_preparation')
        self.assertIsNotNone(started.json()['started_at'])
        self.assertEqual(self.stock_snapshot(), before)
        again = self.client.post(f"{URL}{body['id']}/start/")
        self.assertEqual(again.status_code, 409)
        self.assertEqual(self.client.get(f"{URL}{body['id']}/").json()['started_at'], started.json()['started_at'])

    def test_started_order_cannot_be_edited(self):  # AC-07
        body = self.make_order()
        self.client.post(f"{URL}{body['id']}/start/")
        response = self.client.put(f"{URL}{body['id']}/", {'warehouse_id': str(self.warehouse.id), 'preparations': 1},
                                   format='json')
        self.assertEqual(response.status_code, 409)

    def test_start_fails_with_inactive_warehouse(self):  # EDGE-04
        spare = WarehouseModel.objects.create(company_id=self.company.id, name='Secundario')
        body = self.make_order(warehouse_id=str(spare.id))
        WarehouseModel.objects.filter(pk=spare.pk).update(active=False)
        response = self.client.post(f"{URL}{body['id']}/start/")
        self.assertEqual(response.status_code, 400)
        self.assertIn('warehouse_id', response.json())

    def test_start_allowed_after_recipe_deactivation(self):  # EDGE-03
        body = self.make_order()
        self.client.post(f"/api/recipes/{self.recipe['id']}/deactivate/")
        self.assertEqual(self.client.post(f"{URL}{body['id']}/start/").status_code, 200)

    def test_list_filters_and_pagination(self):  # AC-09
        first = self.make_order()
        second = self.make_order()
        self.client.post(f"{URL}{first['id']}/start/")
        listing = self.client.get(URL).json()
        self.assertEqual([o['number'] for o in listing['results']], [2, 1])
        self.assertEqual([o['id'] for o in self.client.get(URL, {'status': 'draft'}).json()['results']],
                         [second['id']])
        self.assertEqual(self.client.get(URL, {'status': 'in_preparation'}).json()['count'], 1)
        self.assertEqual(self.client.get(URL, {'status': 'x'}).status_code, 400)
        self.assertEqual(self.client.get(URL, {'page': '0'}).status_code, 400)

    def test_warehouses_endpoint(self):  # API-05
        WarehouseModel.objects.create(company_id=self.company.id, name='Inactivo', active=False)
        self.assertEqual(self.client.get(f'{URL}warehouses/').json(),
                         [{'id': str(self.warehouse.id), 'name': 'Central', 'is_default': True}])

    def test_company_isolation_and_module_gate(self):  # AC-10
        body = self.make_order()
        other = make_company('Producción D')
        authenticate(self.client, make_admin(other, username='aislado'))
        self.assertEqual(self.client.get(f"{URL}{body['id']}/").status_code, 403)  # sin módulo en la otra empresa
        self.enable(other)
        self.assertEqual(self.client.get(f"{URL}{body['id']}/").status_code, 404)
        self.assertEqual(self.client.post(f"{URL}{body['id']}/start/").status_code, 404)
        self.assertEqual(self.client.get(URL).json()['count'], 0)
        authenticate(self.client, self.user)
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='production').delete()
        response = self.client.get(URL)
        self.assertEqual((response.status_code, response.json()['code']), (403, 'module_disabled'))

    def test_numbers_are_sequential_per_company(self):  # EDGE-01, INV-08
        from modules.production.infrastructure.django.order_repository import DjangoProductionOrderRepository
        self.make_order()
        other = make_company('Producción E')
        self.assertEqual(DjangoProductionOrderRepository(other.id)._next_number(), 1)
        self.assertEqual(Decimal(self.make_order()['number']), 2)


class OrderNumberConcurrencyTests(TransactionTestCase):
    """EDGE-01: creaciones simultáneas (hilos y conexiones reales) no repiten ni saltan números."""

    THREADS = 8

    def test_concurrent_numbers_are_unique_and_consecutive(self):
        from modules.production.infrastructure.django.order_repository import DjangoProductionOrderRepository
        company = make_company('Producción Concurrente')
        barrier = Barrier(self.THREADS)
        numbers, errors = [], []

        def take_number():
            try:
                barrier.wait(timeout=10)
                with transaction.atomic():
                    numbers.append(DjangoProductionOrderRepository(company.id)._next_number())
            except Exception as exc:  # pragma: no cover - se informa en la aserción
                errors.append(repr(exc))
            finally:
                connection.close()

        threads = [Thread(target=take_number) for _ in range(self.THREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        self.assertEqual(errors, [])
        self.assertEqual(sorted(numbers), list(range(1, self.THREADS + 1)))
