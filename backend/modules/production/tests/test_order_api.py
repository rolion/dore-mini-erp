from decimal import Decimal
from threading import Barrier, Thread
from datetime import timedelta
from uuid import uuid4

from django.db import connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.accounting.infrastructure.django.models import FiscalPeriodModel
from modules.costing import services as costing_services
from modules.costing.domain.valuation import ValuationAdoption, parse_lines
from modules.costing.infrastructure.django.repositories import DjangoAdoptionRepository
from modules.inventory import services as inventory_services
from modules.inventory.infrastructure.django.models import StockLotModel, StockMovementModel, WarehouseModel
from modules.catalog.infrastructure.django.models import ProductModel, UnitModel
from modules.sales.tests.periods import open_test_period
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

    # --- DORE-PROD-004: pasar a refrigeración ------------------------------------------------------------------

    def prepare_stock(self, cheese='20', flour='30'):
        open_test_period(self.company.id)
        ProductModel.objects.filter(pk__in=[self.cheese.pk, self.flour.pk, self.result.pk]).update(tracks_stock=True)
        for product, quantity in ((self.cheese, cheese), (self.flour, flour)):
            inventory_services.record_movement(
                self.company.id, product_id=product.id, warehouse_id=self.warehouse.id, kind='in',
                quantity=Decimal(quantity), user_id=self.user.id, user_name='prod-admin', reference='Seed')

    def started_order(self, **changes):
        body = self.make_order(**changes)
        self.assertEqual(self.client.post(f"{URL}{body['id']}/start/").status_code, 200)
        return body

    def refrigerate_payload(self, order, cheese=None, flour=None, output='118', **changes):
        lines = {line['product_name']: line['expected_quantity'] for line in order['ingredients']}
        body = {'entered_at': timezone.now().isoformat(), 'actual_output': output,
                'ingredients': [{'product_id': str(self.cheese.id), 'actual_quantity': cheese or lines['Queso']},
                                {'product_id': str(self.flour.id), 'actual_quantity': flour or lines['Almidón']}]}
        body.update(changes)
        return body

    def refrigerate(self, order, **payload):
        return self.client.post(f"{URL}{order['id']}/refrigerate/", self.refrigerate_payload(order, **payload),
                                format='json')

    def test_refrigerate_registers_real_production_and_lot(self):  # AC-01, AC-02, AC-09, INV-06
        self.prepare_stock()
        order = self.started_order()
        response = self.refrigerate(order, cheese='7', output='118')  # previstos: 7.5 / 10 / 120
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['status'], body['actual_output'], body['expected_output']),
                         ('refrigerating', '118.0000', '120.0000'))
        self.assertEqual([(i['expected_quantity'], i['actual_quantity']) for i in body['ingredients']],
                         [('7.5000', '7.0000'), ('10.0000', '10.0000')])
        self.assertTrue(body['lot']['code'].startswith('L-'))
        self.assertIsNotNone(body['entered_at'])
        self.assertIsNone(body['cost_total'])
        wh = self.warehouse.id
        self.assertEqual((inventory_services.get_balance(self.company.id, self.cheese.id, wh),
                          inventory_services.get_balance(self.company.id, self.flour.id, wh),
                          inventory_services.get_balance(self.company.id, self.result.id, wh)),
                         (Decimal('13'), Decimal('20'), Decimal('118')))
        lot = inventory_services.get_lot(self.company.id, body['lot']['id'])
        self.assertEqual((lot.status, lot.physical_quantity, lot.available_quantity),
                         ('refrigerating', Decimal('118'), Decimal('0')))
        self.assertEqual(self.client.get(f"{URL}{order['id']}/").json(), body)
        self.assertEqual(self.client.get(f'{URL}?status=refrigerating').json()['count'], 1)

    def test_refrigerate_shortage_changes_nothing(self):  # AC-03, INV-04
        self.prepare_stock(cheese='5', flour='4')  # se necesitan 7.5 y 10
        order = self.started_order()
        before = self.stock_snapshot()
        response = self.refrigerate(order)
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()['code'], 'insufficient_stock')
        self.assertEqual(sorted((s['product_name'], s['requested'], s['available'], s['missing'])
                                for s in response.json()['shortages']),
                         [('Almidón', '10.0000', '4.0000', '6.0000'), ('Queso', '7.5000', '5.0000', '2.5000')])
        self.assertEqual(self.stock_snapshot(), before)
        self.assertEqual(self.client.get(f"{URL}{order['id']}/").json()['status'], 'in_preparation')

    def test_refrigerate_twice_does_not_duplicate_movements(self):  # AC-04, EDGE-03
        self.prepare_stock()
        order = self.started_order()
        self.assertEqual(self.refrigerate(order).status_code, 200)
        after = self.stock_snapshot()
        again = self.refrigerate(order)
        self.assertEqual(again.status_code, 409)
        self.assertEqual(self.stock_snapshot(), after)

    def test_refrigerate_requires_an_order_in_preparation(self):  # AC-06
        self.prepare_stock()
        draft = self.make_order()
        self.assertEqual(self.refrigerate(draft).status_code, 409)
        self.assertEqual(self.stock_snapshot()['lots'], 0)

    def test_refrigerate_validates_input(self):  # AC-06, INV-02, INV-03
        self.prepare_stock()
        order = self.started_order()
        cases = [
            ('actual_output', {'output': '0'}), ('actual_output', {'output': '-1'}),
            ('actual_output', {'output': 'abc'}), ('actual_output', {'output': None}),
            ('actual_output', {'output': '1.23456'}),
            ('entered_at', {'entered_at': '2020-01-01T00:00:00Z'}),
            ('entered_at', {'entered_at': (timezone.now() + timedelta(days=1)).isoformat()}),
            ('ingredients', {'ingredients': []}),
            ('ingredients', {'ingredients': [{'product_id': str(self.cheese.id), 'actual_quantity': '1'},
                                             {'product_id': str(self.cheese.id), 'actual_quantity': '1'}]}),
            ('ingredients', {'ingredients': [{'product_id': str(self.cheese.id), 'actual_quantity': '-1'},
                                             {'product_id': str(self.flour.id), 'actual_quantity': '1'}]}),
            ('ingredients', {'ingredients': [{'product_id': str(self.cheese.id), 'actual_quantity': '1'},
                                             {'product_id': str(uuid4()), 'actual_quantity': '1'}]}),
        ]
        before = self.stock_snapshot()
        for field, extra in cases:
            with self.subTest(extra=extra):
                payload = self.refrigerate_payload(order)
                if 'output' in extra:
                    payload['actual_output'] = extra['output']
                else:
                    payload.update(extra)
                response = self.client.post(f"{URL}{order['id']}/refrigerate/", payload, format='json')
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(field, response.json())
        self.assertEqual(self.stock_snapshot(), before)

    def test_refrigerate_allows_zero_consumption_lines(self):  # EDGE-01
        self.prepare_stock()
        order = self.started_order()
        response = self.refrigerate(order, cheese='0')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(inventory_services.get_balance(self.company.id, self.cheese.id, self.warehouse.id),
                         Decimal('20'))
        self.assertEqual(StockMovementModel.objects.filter(source_type='production_order', kind='out').count(), 1)

    def test_refrigerate_without_open_fiscal_period_changes_nothing(self):  # AC-07
        self.prepare_stock()
        FiscalPeriodModel.objects.filter(company_id=self.company.id).delete()
        order = self.started_order()
        before = self.stock_snapshot()
        response = self.refrigerate(order)
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()['code'], 'fiscal_period_missing')
        self.assertEqual(self.stock_snapshot(), before)
        self.assertEqual(self.client.get(f"{URL}{order['id']}/").json()['status'], 'in_preparation')

    def test_refrigerate_records_cost_with_valuation(self):  # AC-05, INV-07
        self.prepare_stock()
        CompanyModuleModel.objects.create(company_id=self.company.id, module_key='costing')
        lines = parse_lines([
            {'product_id': self.cheese.id, 'reconciled_quantity': '20', 'total_value': '200.00',
             'declared_zero': False, 'source': None},
            {'product_id': self.flour.id, 'reconciled_quantity': '30', 'total_value': '60.00',
             'declared_zero': False, 'source': None}])
        DjangoAdoptionRepository(self.company.id).save(
            ValuationAdoption.adopt(uuid4(), timezone.now(), None, 'ana', lines))
        order = self.started_order()
        response = self.refrigerate(order, output='100')  # 7.5×10 + 10×2 = 95.00
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['cost_total'], '95.00')
        self.assertEqual(costing_services.get_average_costs(self.company.id, [self.result.id]),
                         {self.result.id: Decimal('0.950000')})

    def test_refrigerate_isolation_and_module_gate(self):  # AC-08
        self.prepare_stock()
        order = self.started_order()
        other = make_company('Producción B')
        authenticate(self.client, make_admin(other, username='other-admin'))
        self.enable(other)
        response = self.client.post(f"{URL}{order['id']}/refrigerate/", self.refrigerate_payload(order), format='json')
        self.assertEqual(response.status_code, 404)
        authenticate(self.client, self.user)
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='production').delete()
        response = self.refrigerate(order)
        self.assertEqual((response.status_code, response.json().get('code')), (403, 'module_disabled'))

    def test_refrigeration_movements_cannot_be_reversed_from_inventory(self):  # AC-10
        self.prepare_stock()
        order = self.started_order()
        self.assertEqual(self.refrigerate(order).status_code, 200)
        movement = StockMovementModel.objects.filter(source_type='production_order', kind='out').first()
        with self.assertRaises(inventory_services.MovementConflict):
            inventory_services.reverse_movement(
                self.company.id, movement.id, user_id=None, user_name='ana', reason='Prueba', manual_only=True)

    def test_refrigerate_rejects_fractions_for_whole_units(self):  # INV-02
        self.prepare_stock()
        order = self.started_order()
        response = self.refrigerate(order, output='118.5')  # el granel se cuenta en unidades enteras
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('actual_output', response.json())
        self.assertEqual(self.client.get(f"{URL}{order['id']}/").json()['status'], 'in_preparation')
        egg = self.product('Huevo', self.unit)
        ProductModel.objects.filter(pk=egg.pk).update(tracks_stock=True)
        inventory_services.record_movement(
            self.company.id, product_id=egg.id, warehouse_id=self.warehouse.id, kind='in', quantity=Decimal('50'),
            user_id=self.user.id, user_name='prod-admin', reference='Seed')
        recipe = self.create(name='Con huevo', ingredients=[
            {'product_id': str(egg.id), 'unit_id': str(self.unit.id), 'quantity': '2'}])
        eggs = self.make_order(recipe_id=recipe['id'])
        self.assertEqual(self.client.post(f"{URL}{eggs['id']}/start/").status_code, 200)
        before = self.stock_snapshot()
        response = self.client.post(
            f"{URL}{eggs['id']}/refrigerate/",
            {'entered_at': timezone.now().isoformat(), 'actual_output': '118',
             'ingredients': [{'product_id': str(egg.id), 'actual_quantity': '9.5'}]}, format='json')
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()['ingredients'],
                         [{'actual_quantity': ['Este ingrediente solo admite cantidades enteras.']}])
        self.assertEqual(self.stock_snapshot(), before)

    def test_refrigerate_flags_the_line_of_an_ingredient_without_stock_control(self):  # EDGE-05
        self.prepare_stock()
        ProductModel.objects.filter(pk=self.flour.pk).update(tracks_stock=False)
        order = self.started_order()
        before = self.stock_snapshot()
        response = self.refrigerate(order)
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()['ingredients'],
                         [{}, {'actual_quantity': ['El ingrediente no controla stock.']}])
        self.assertEqual(self.stock_snapshot(), before)

    def test_refrigerate_with_a_deactivated_warehouse_changes_nothing(self):  # EDGE-04, S5
        self.prepare_stock()
        order = self.started_order()
        before = self.stock_snapshot()
        WarehouseModel.objects.filter(pk=self.warehouse.pk).update(active=False)
        response = self.refrigerate(order)
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(self.stock_snapshot(), before)
        self.assertEqual(self.client.get(f"{URL}{order['id']}/").json()['status'], 'in_preparation')

    def test_refrigerate_without_average_cost_keeps_cost_empty(self):  # AC-05, INV-07, S2
        self.prepare_stock()
        CompanyModuleModel.objects.create(company_id=self.company.id, module_key='costing')
        lines = parse_lines([
            {'product_id': self.cheese.id, 'reconciled_quantity': '20', 'total_value': '200.00',
             'declared_zero': False, 'source': None}])  # el almidón no tiene costo promedio
        DjangoAdoptionRepository(self.company.id).save(
            ValuationAdoption.adopt(uuid4(), timezone.now(), None, 'ana', lines))
        order = self.started_order()
        response = self.refrigerate(order)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.json()['cost_total'])
        self.assertEqual(costing_services.get_average_costs(self.company.id, [self.result.id]), {})

    def test_list_filter_message_names_refrigerating(self):  # AC-09
        response = self.client.get(URL, {'status': 'x'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('refrigerating', response.json()['status'][0])


class OrderReleaseApiTests(OrderApiTests):
    def refrigerated(self, hours_ago=0):
        self.prepare_stock()
        order = self.started_order()
        self.assertEqual(self.refrigerate(order).status_code, 200)
        if hours_ago:
            from modules.production.infrastructure.django.models import ProductionOrderModel
            ProductionOrderModel.objects.filter(pk=order['id']).update(
                entered_at=timezone.now() - timedelta(hours=hours_ago))
        return order

    def release(self, order):
        return self.client.post(f"{URL}{order['id']}/release/")

    def lot_state(self, order):
        lot = inventory_services.get_lot(self.company.id, self.client.get(f"{URL}{order['id']}/").json()['lot']['id'])
        return lot.status, lot.physical_quantity, lot.available_quantity

    def movements(self):
        return StockMovementModel.objects.filter(company_id=self.company.id).count()

    def test_detail_shows_release_data(self):  # AC-01, API-02
        order = self.refrigerated(hours_ago=1)
        body = self.client.get(f"{URL}{order['id']}/").json()
        self.assertEqual((body['release']['min_hours'], body['release']['can_release']), (12, False))
        entered = timezone.datetime.fromisoformat(body['entered_at'].replace('Z', '+00:00'))
        first = timezone.datetime.fromisoformat(body['release']['releasable_from'].replace('Z', '+00:00'))
        self.assertEqual(first - entered, timedelta(hours=12))
        self.assertIsNone(self.client.get(f"{URL}{self.make_order()['id']}/").json()['release'])

    def test_release_before_minimum_is_rejected_and_changes_nothing(self):  # AC-02, INV-02
        order = self.refrigerated(hours_ago=11)
        before = (self.movements(), self.lot_state(order))
        response = self.release(order)
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual((response.json()['code'], response.json()['min_hours']), ('release_too_early', '12'))
        self.assertIn('releasable_from', response.json())
        self.assertEqual((self.movements(), self.lot_state(order)), before)
        self.assertEqual(self.client.get(f"{URL}{order['id']}/").json()['status'], 'refrigerating')

    def test_release_after_minimum_makes_the_lot_available(self):  # AC-03, AC-04, INV-03, INV-06
        order = self.refrigerated(hours_ago=13)
        self.assertEqual(self.lot_state(order), ('refrigerating', Decimal('118'), Decimal('0')))
        moves = self.movements()
        response = self.release(order)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['status'], body['released_by']), ('ready_to_pack', 'prod-admin'))
        self.assertIsNotNone(body['released_at'])
        self.assertEqual(self.lot_state(order), ('released', Decimal('118'), Decimal('118')))
        self.assertEqual(self.movements(), moves)
        self.assertEqual(inventory_services.get_balance(self.company.id, self.result.id, self.warehouse.id),
                         Decimal('118'))
        self.assertEqual(self.client.get(f'{URL}?status=ready_to_pack').json()['count'], 1)

    def test_release_twice_does_not_duplicate_anything(self):  # AC-05, INV-05
        order = self.refrigerated(hours_ago=13)
        first = self.release(order).json()
        moves = self.movements()
        again = self.release(order)
        self.assertEqual(again.status_code, 200, again.content)
        self.assertEqual((again.json()['released_at'], self.movements(), self.lot_state(order)),
                         (first['released_at'], moves, ('released', Decimal('118'), Decimal('118'))))

    def test_release_requires_a_refrigerating_order(self):  # AC-06, INV-01
        self.prepare_stock()
        for order in (self.make_order(), self.started_order()):
            response = self.release(order)
            self.assertEqual(response.status_code, 409, response.content)
            self.assertIn('refrigeración', response.json()['detail'])

    def test_minimum_comes_from_the_company_setting(self):  # AC-07, EDGE-01
        order = self.refrigerated(hours_ago=1)
        self.assertEqual(self.release(order).status_code, 409)
        response = self.client.patch('/api/settings/production/',
                                     {'settings': {'production.min_refrigeration_hours': '0'}}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.release(order).status_code, 200)

    def test_release_isolation_and_module_gate(self):  # AC-09
        order = self.refrigerated(hours_ago=13)
        other = make_company('Producción B')
        authenticate(self.client, make_admin(other, username='other-admin'))
        self.assertEqual(self.release(order).status_code, 403)  # módulo no habilitado
        self.enable(other)
        self.assertEqual(self.release(order).status_code, 404)
        self.assertEqual(self.lot_state_by_id(order), 'refrigerating')

    def lot_state_by_id(self, order):
        return StockLotModel.objects.get(company_id=self.company.id).status


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


class OrderRefrigerateConcurrencyTests(TransactionTestCase):
    """EDGE-03: dos envíos simultáneos (hilos y conexiones reales): uno gana, el otro recibe 409, sin duplicar."""

    def test_two_simultaneous_submissions_register_once(self):
        from rest_framework.test import APIClient
        company = make_company('Producción Carrera')
        user = make_admin(company, username='carrera-admin')
        CompanySettingsModel.objects.create(company_id=company.id)
        CompanyModuleModel.objects.create(company_id=company.id, module_key='production')
        unit = UnitModel.objects.create(company_id=company.id, name='Unidad', abbreviation='u')
        kilo = UnitModel.objects.create(company_id=company.id, name='Kilogramo', abbreviation='kg',
                                        allows_fractions=True)
        make = lambda name, base: ProductModel.objects.create(  # noqa: E731
            company_id=company.id, name=name, base_unit=base, sale_price=Decimal('1.00'), tracks_stock=True)
        result, cheese = make('Cuñapé', unit), make('Queso', kilo)
        warehouse = WarehouseModel.objects.create(company_id=company.id, name='Central', is_default=True)
        open_test_period(company.id)
        inventory_services.record_movement(
            company.id, product_id=cheese.id, warehouse_id=warehouse.id, kind='in', quantity=Decimal('20'),
            user_id=user.id, user_name='carrera-admin', reference='Seed')
        client = APIClient()
        authenticate(client, user)
        recipe = client.post('/api/recipes/', {
            'name': 'Q', 'result_product_id': str(result.id), 'yield_quantity': '24',
            'ingredients': [{'product_id': str(cheese.id), 'unit_id': str(kilo.id), 'quantity': '1.5'}]},
            format='json').json()
        order = client.post(URL, {'recipe_id': recipe['id'], 'warehouse_id': str(warehouse.id), 'preparations': 5},
                            format='json').json()
        client.post(f"{URL}{order['id']}/start/")
        payload = {'entered_at': timezone.now().isoformat(), 'actual_output': '118',
                   'ingredients': [{'product_id': str(cheese.id), 'actual_quantity': '7.5'}]}
        barrier, statuses = Barrier(2), []

        def submit():
            try:
                worker = APIClient()
                authenticate(worker, user)
                barrier.wait(timeout=10)
                statuses.append(worker.post(f"{URL}{order['id']}/refrigerate/", payload, format='json').status_code)
            except Exception as exc:  # pragma: no cover - se informa en la aserción
                statuses.append(repr(exc))
            finally:
                connection.close()

        threads = [Thread(target=submit) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        self.assertEqual(sorted(statuses), [200, 409])
        self.assertEqual(StockLotModel.objects.filter(company_id=company.id).count(), 1)
        self.assertEqual(StockMovementModel.objects.filter(company_id=company.id, source_type='production_order')
                         .count(), 2)  # una salida de queso y una entrada del lote
        self.assertEqual(inventory_services.get_balance(company.id, cheese.id, warehouse.id), Decimal('12.5'))
