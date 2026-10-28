"""PB-INV-003: apertura de existencias (movimientos y saldos), idempotencia y lecturas."""
from datetime import timedelta
from decimal import Decimal
from threading import Barrier, Thread
from uuid import UUID, uuid4

from django.db import IntegrityError, connection, transaction
from django.test import SimpleTestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.inventory.application.stock_use_cases import RegisterOpening
from modules.inventory.domain.exceptions import OpeningValidationError
from modules.inventory.domain.stock import StockOpening
from modules.inventory.infrastructure.catalog_adapter import CatalogProducts
from modules.inventory.infrastructure.django.models import StockBalanceModel, StockMovementModel, WarehouseModel
from modules.inventory.infrastructure.django.stock_repository import DjangoStockRepository, has_movements
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled
from shared import stock_history

TODAY = timezone.localdate()
OPENINGS = '/api/stock/openings/'
STOCK = '/api/stock/'


def line(product_id, quantity='10'):
    return {'product_id': str(product_id), 'quantity': quantity}


class OpeningDomainTests(SimpleTestCase):
    def create(self, **overrides):
        values = {'opening_id': uuid4(), 'warehouse_id': uuid4(), 'movement_date': TODAY,
                  'reference': ' Inventario inicial ', 'lines': [(uuid4(), '5')], 'today': TODAY, **overrides}
        return StockOpening.create(**values)

    def errors(self, **overrides):
        with self.assertRaises(OpeningValidationError) as ctx:
            self.create(**overrides)
        return ctx.exception.errors

    def test_valid_opening_trims_reference_and_normalises_quantity(self):  # AC-01, INV-01, INV-02
        opening = self.create(lines=[(uuid4(), '5'), (uuid4(), Decimal('0.5'))])
        self.assertEqual(opening.reference, 'Inventario inicial')
        self.assertEqual([line.quantity for line in opening.lines], [Decimal('5.000'), Decimal('0.500')])

    def test_zero_quantity_is_allowed(self):  # EDGE-01
        self.assertEqual(self.create(lines=[(uuid4(), '0')]).lines[0].quantity, Decimal('0.000'))

    def test_reference_is_required_and_limited(self):  # INV-01
        self.assertIn('reference', self.errors(reference='  '))
        self.assertIn('reference', self.errors(reference='x' * 101))

    def test_future_date_is_rejected_but_today_and_past_are_fine(self):  # EDGE-05
        self.assertIn('movement_date', self.errors(movement_date=TODAY + timedelta(days=1)))
        self.create(movement_date=TODAY - timedelta(days=30))

    def test_needs_at_least_one_line(self):  # EDGE-05
        self.assertIn('lines', self.errors(lines=[]))

    def test_repeated_product_is_flagged_on_the_second_line(self):  # AC-04
        product = uuid4()
        errors = self.errors(lines=[(product, '1'), (product, '2')])
        self.assertEqual(errors['lines'][0], {})
        self.assertIn('product_id', errors['lines'][1])

    def test_quantity_must_be_a_non_negative_decimal_with_three_places(self):  # EDGE-02
        for bad in ('-1', '1.0005', 'abc', 1.5, True, None, 'NaN', '100000000000'):
            self.assertIn('quantity', self.errors(lines=[(uuid4(), bad)])['lines'][0], bad)

    def test_same_content_ignores_line_order(self):  # INV-07
        a, b = uuid4(), uuid4()
        base = {'opening_id': uuid4(), 'warehouse_id': uuid4(), 'movement_date': TODAY}
        one = self.create(**base, lines=[(a, '1'), (b, '2')])
        two = self.create(**base, lines=[(b, '2'), (a, '1')])
        other = self.create(**base, lines=[(a, '1'), (b, '3')])
        self.assertTrue(one.same_content_as(two))
        self.assertFalse(one.same_content_as(other))


class StockApiTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.admin = make_admin(self.company, username='ana')
        authenticate(self.client, self.admin)
        set_enabled(self.company, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        self.unit = self.make_unit('Unidad', 'u', fractions=False)
        self.kilo = self.make_unit('Kilogramo', 'kg', fractions=True)
        self.warehouse = self.client.get('/api/warehouses/').json()['results'][0]['id']

    def make_unit(self, name, abbreviation, fractions):
        response = self.client.post(
            '/api/units/', {'name': name, 'abbreviation': abbreviation, 'allows_fractions': fractions}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()['id']

    def make_product(self, name='Harina', unit=None, tracks=True, client=None):
        body = {'name': name, 'sale_price': '10.00'}
        if tracks:
            body.update(tracks_stock=True, base_unit_id=unit or self.unit)
        response = (client or self.client).post('/api/products/', body, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()['id']

    def open(self, lines, opening_id=None, warehouse=None, **extra):
        body = {'opening_id': str(opening_id or uuid4()), 'warehouse_id': warehouse or self.warehouse,
                'movement_date': TODAY.isoformat(), 'reference': 'Apertura 2026', 'lines': lines, **extra}
        return self.client.post(OPENINGS, body, format='json')

    def counts(self):
        return StockMovementModel.objects.count(), StockBalanceModel.objects.count()


class OpeningApiTests(StockApiTestCase):
    def test_confirming_creates_movements_and_balances(self):  # AC-01, AC-02
        flour, sugar = self.make_product('Harina'), self.make_product('Azúcar', self.kilo)
        response = self.open([line(flour, '10'), line(sugar, '2.5')])
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['reference'], 'Apertura 2026')
        self.assertEqual({entry['product_id']: entry['quantity'] for entry in body['lines']},
                         {flour: '10.000', sugar: '2.500'})
        movements = StockMovementModel.objects.filter(company_id=self.company.id)
        self.assertEqual(movements.count(), 2)
        self.assertEqual({m.movement_type for m in movements}, {'opening'})
        self.assertEqual({m.created_by_id for m in movements}, {self.admin.pk})
        self.assertEqual(
            {str(b.product_id): b.quantity for b in StockBalanceModel.objects.filter(company_id=self.company.id)},
            {flour: Decimal('10.000'), sugar: Decimal('2.500')})

    def test_zero_quantity_creates_a_movement_and_a_zero_balance(self):  # EDGE-01
        product = self.make_product()
        self.assertEqual(self.open([line(product, '0')]).status_code, 201)
        self.assertEqual(StockBalanceModel.objects.get(product_id=product).quantity, Decimal('0.000'))
        self.assertEqual(self.open([line(product, '5')]).status_code, 409)  # ya consumió su apertura

    def test_retrying_with_the_same_key_returns_the_original_without_duplicating(self):  # AC-02, INV-07
        product = self.make_product()
        key = uuid4()
        first = self.open([line(product, '10')], opening_id=key)
        before = self.counts()
        again = self.open([line(product, '10')], opening_id=key)
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(again.json(), first.json())
        self.assertEqual(self.counts(), before)

    def test_same_key_with_other_content_is_a_conflict(self):  # EDGE-07
        product = self.make_product()
        key = uuid4()
        self.open([line(product, '10')], opening_id=key)
        response = self.open([line(product, '11')], opening_id=key)
        self.assertEqual((response.status_code, response.json()['code']), (409, 'opening_id_reused'))
        self.assertEqual(StockBalanceModel.objects.get(product_id=product).quantity, Decimal('10.000'))

    def test_product_with_movements_is_rejected_and_nothing_is_created(self):  # AC-03, INV-04, INV-06
        taken, free = self.make_product('Harina'), self.make_product('Sal')
        self.open([line(taken, '1')])
        before = self.counts()
        response = self.open([line(free, '3'), line(taken, '9')])
        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body['code'], 'stock_history_exists')
        self.assertEqual(body['lines'], [{'index': '1', 'product_id': taken}])
        self.assertEqual(self.counts(), before)

    def test_same_product_in_another_warehouse_is_a_separate_opening(self):  # INV-04
        product = self.make_product()
        other = self.client.post('/api/warehouses/', {'name': 'Tienda'}, format='json').json()['id']
        self.assertEqual(self.open([line(product, '1')]).status_code, 201)
        self.assertEqual(self.open([line(product, '2')], warehouse=other).status_code, 201)

    def test_fractions_follow_the_unit(self):  # EDGE-02, INV-02
        pieces, kilos = self.make_product('Piezas'), self.make_product('Granel', self.kilo)
        response = self.open([line(pieces, '1.5'), line(kilos, '1.5')])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['lines'][0].keys(), {'quantity'})
        self.assertEqual(response.json()['lines'][1], {})
        self.assertEqual(self.counts(), (0, 0))

    def test_invalid_lines_are_reported_by_position(self):  # EDGE-02, EDGE-04
        untracked = self.make_product('Servicio', tracks=False)
        response = self.open([line(untracked), line(uuid4()), line(self.make_product(), '-1')])
        self.assertEqual(response.status_code, 400)
        errors = response.json()['lines']
        self.assertEqual([sorted(entry) for entry in errors], [[], [], ['quantity']])  # forma/dominio primero
        response = self.open([line(untracked), line(uuid4())])
        self.assertEqual([list(entry) for entry in response.json()['lines']], [['product_id'], ['product_id']])
        self.assertEqual(self.counts(), (0, 0))

    def test_header_validation(self):  # EDGE-05, INV-01
        product = self.make_product()
        tomorrow = (TODAY + timedelta(days=1)).isoformat()
        self.assertIn('movement_date', self.open([line(product)], movement_date=tomorrow).json())
        self.assertIn('reference', self.open([line(product)], reference=' ').json())
        self.assertIn('lines', self.open([]).json())
        repeated = self.open([line(product), line(product)])
        self.assertEqual(repeated.status_code, 400)
        self.assertIn('product_id', repeated.json()['lines'][1])

    def test_warehouse_must_exist_belong_to_the_company_and_be_active(self):  # EDGE-04, INV-03
        product = self.make_product()
        self.assertEqual(self.open([line(product)], warehouse=str(uuid4())).status_code, 404)
        spare = self.client.post('/api/warehouses/', {'name': 'Bodega'}, format='json').json()['id']
        self.client.post(f'/api/warehouses/{spare}/deactivate/')
        response = self.open([line(product)], warehouse=spare)
        self.assertEqual(response.status_code, 400)
        self.assertIn('warehouse_id', response.json())

    def test_other_company_data_is_unreachable(self):  # INV-03, aislamiento
        product = self.make_product()
        other = make_company('Empresa B')
        client = APIClient()
        authenticate(client, make_admin(other, username='beto'))
        set_enabled(other, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        own = client.get('/api/warehouses/').json()['results'][0]['id']
        body = {'opening_id': str(uuid4()), 'movement_date': TODAY.isoformat(), 'reference': 'x'}
        foreign_warehouse = client.post(
            OPENINGS, {**body, 'warehouse_id': self.warehouse, 'lines': [line(product)]}, format='json')
        foreign_product = client.post(
            OPENINGS, {**body, 'warehouse_id': own, 'lines': [line(product)]}, format='json')
        self.assertEqual(foreign_warehouse.status_code, 404)
        self.assertEqual((foreign_product.status_code, foreign_product.json()['lines'][0].keys()), (400, {'product_id'}))
        self.assertEqual(self.counts(), (0, 0))

    def test_requires_the_inventory_module(self):  # EDGE-06
        product = self.make_product()
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)
        self.assertEqual(self.open([line(product)]).status_code, 403)
        self.assertEqual(self.client.get(STOCK).status_code, 403)

    def test_database_allows_one_opening_per_product_and_warehouse(self):  # INV-04 (defensa final)
        product = self.make_product()
        self.open([line(product)])
        warehouse = WarehouseModel.objects.get(pk=self.warehouse)
        with self.assertRaises(IntegrityError), transaction.atomic():
            StockMovementModel.objects.create(
                company_id=self.company.id, warehouse=warehouse, product_id=product, movement_type='opening',
                quantity=Decimal('1'), movement_date=TODAY, reference='x', opening_id=uuid4())
        with self.assertRaises(IntegrityError), transaction.atomic():
            StockMovementModel.objects.create(
                company_id=self.company.id, warehouse=warehouse, product_id=uuid4(), movement_type='opening',
                quantity=Decimal('-1'), movement_date=TODAY, reference='x', opening_id=uuid4())


class StockReadTests(StockApiTestCase):
    def test_stock_list_is_enriched_and_filterable_by_warehouse(self):  # AC-05, API-02
        product = self.make_product('Harina')
        other = self.client.post('/api/warehouses/', {'name': 'Tienda'}, format='json').json()['id']
        self.open([line(product, '7')])
        self.open([line(self.make_product('Sal', self.kilo), '1.5')], warehouse=other)
        rows = self.client.get(STOCK, {'warehouse_id': self.warehouse}).json()['results']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['product_name'], 'Harina')
        self.assertEqual((rows[0]['quantity'], rows[0]['warehouse_name']), ('7.000', 'Almacén principal'))
        self.assertEqual(rows[0]['unit'], {'name': 'Unidad', 'abbreviation': 'u', 'allows_fractions': False})
        self.assertEqual(self.client.get(STOCK).json()['count'], 2)
        self.assertEqual(self.client.get(STOCK, {'warehouse_id': 'nope'}).status_code, 400)

    def test_stock_is_isolated_between_companies(self):  # aislamiento
        self.open([line(self.make_product(), '7')])
        other = make_company('Empresa B')
        client = APIClient()
        authenticate(client, make_admin(other, username='beto'))
        set_enabled(other, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        self.assertEqual(client.get(STOCK).json()['count'], 0)
        response = client.get(f'{STOCK}movements/', {'warehouse_id': self.warehouse, 'product_id': uuid4()})
        self.assertEqual(response.status_code, 404)

    def test_movements_of_a_product_in_a_warehouse(self):  # AC-05, API-03
        product = self.make_product()
        self.open([line(product, '4')], reference='Cierre de año')
        response = self.client.get(f'{STOCK}movements/', {'warehouse_id': self.warehouse, 'product_id': product})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([(m['movement_type'], m['quantity'], m['reference']) for m in body['results']],
                         [('opening', '4.000', 'Cierre de año')])
        self.assertEqual((body['summary']['product_name'], body['summary']['quantity']), ('Harina', '4.000'))
        self.assertEqual(self.client.get(f'{STOCK}movements/').status_code, 400)

    def test_opening_check_lists_products_with_history(self):  # AC-03, API-04
        taken, free = self.make_product('Harina'), self.make_product('Sal')
        self.open([line(taken)])
        response = self.client.get(
            f'{STOCK}opening-check/?warehouse_id={self.warehouse}&product_id={taken}&product_id={free}')
        self.assertEqual(response.json(), {'products_with_history': [taken]})
        empty = self.client.get(f'{STOCK}opening-check/?warehouse_id={self.warehouse}')
        self.assertEqual(empty.json(), {'products_with_history': []})


class ConnectedPortsTests(StockApiTestCase):
    def setUp(self):
        super().setUp()
        # `InventoryConfig.ready()` registra el proveedor real; otras pruebas lo reemplazan por dobles, así que
        # se restablece aquí y se devuelve el anterior al terminar.
        previous = stock_history._provider
        stock_history.register(has_movements)
        self.addCleanup(stock_history.register, previous)

    def test_opening_locks_unit_and_stock_control_in_catalog(self):  # AC-06
        product = self.make_product()
        self.open([line(product)])
        response = self.client.patch(f'/api/products/{product}/', {'base_unit_id': self.kilo}, format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'stock_history_locked'))
        response = self.client.patch(f'/api/products/{product}/', {'tracks_stock': False}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.patch(f'/api/products/{product}/', {'name': 'Otro'}, format='json').status_code, 200)

    def test_warehouse_with_stock_cannot_be_deactivated_but_empty_one_can(self):  # AC-06
        product = self.make_product()
        spare = self.client.post('/api/warehouses/', {'name': 'Bodega'}, format='json').json()['id']
        self.open([line(product, '3')], warehouse=spare)
        response = self.client.post(f'/api/warehouses/{spare}/deactivate/')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'warehouse_has_stock'))
        empty = self.client.post('/api/warehouses/', {'name': 'Vacía'}, format='json').json()['id']
        zero = self.make_product('Cero')
        self.open([line(zero, '0')], warehouse=empty)
        self.assertEqual(self.client.post(f'/api/warehouses/{empty}/deactivate/').status_code, 200)


class ConcurrentOpeningTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('Empresa C')
        admin = make_admin(self.company, username='carla')
        client = APIClient()
        authenticate(client, admin)
        set_enabled(self.company, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        unit = client.post('/api/units/', {'name': 'Unidad', 'abbreviation': 'u'}, format='json').json()['id']
        self.product = client.post('/api/products/', {
            'name': 'Harina', 'sale_price': '1.00', 'tracks_stock': True, 'base_unit_id': unit}, format='json').json()['id']
        self.warehouse = client.get('/api/warehouses/').json()['results'][0]['id']

    def run_parallel(self, keys):
        barrier = Barrier(len(keys))
        outcomes = []

        def attempt(key):
            try:
                barrier.wait()
                use_case = RegisterOpening(DjangoStockRepository(self.company.id), CatalogProducts(self.company.id))
                try:
                    outcome = use_case.execute(
                        opening_id=key, warehouse_id=UUID(self.warehouse), movement_date=TODAY, reference='Apertura',
                        lines=[(UUID(self.product), '5')], today=TODAY)
                    outcomes.append('replayed' if outcome.replayed else 'created')
                except Exception as exc:  # noqa: BLE001 - se reporta el tipo para la aserción
                    outcomes.append(type(exc).__name__)
            finally:
                connection.close()

        threads = [Thread(target=attempt, args=(key,)) for key in keys]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return sorted(outcomes)

    def test_double_submit_with_the_same_key_creates_one_opening(self):  # EDGE-03, AC-02
        key = uuid4()
        self.assertEqual(self.run_parallel([key, key]), ['created', 'replayed'])
        self.assertEqual(StockMovementModel.objects.filter(company_id=self.company.id).count(), 1)
        self.assertEqual(StockBalanceModel.objects.filter(company_id=self.company.id).count(), 1)

    def test_two_keys_for_the_same_product_create_only_one(self):  # EDGE-03, INV-04
        self.assertEqual(self.run_parallel([uuid4(), uuid4()]), ['StockHistoryExists', 'created'])
        self.assertEqual(StockMovementModel.objects.filter(company_id=self.company.id).count(), 1)
