"""PB-INV-003: apertura de existencias (movimientos y saldos), idempotencia y lecturas."""
from datetime import timedelta
from decimal import Decimal
from threading import Barrier, Thread
from uuid import UUID, uuid4

from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.inventory.application.stock_use_cases import RegisterOpening
from modules.inventory.domain.exceptions import OpeningValidationError
from modules.inventory.domain.stock import StockOpening
from modules.inventory.infrastructure.adapters import CatalogProductDirectory
from modules.inventory.infrastructure.django.models import StockMovementModel
from modules.inventory.infrastructure.django.movement_repository import DjangoStockMovementRepository
from modules.inventory.infrastructure.django.repositories import DjangoWarehouseRepository
from modules.inventory.services import get_balance, has_history
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

    def test_zero_quantity_is_accepted_but_not_recorded(self):  # EDGE-01
        product = uuid4()
        opening = self.create(lines=[(uuid4(), '0'), (product, '3')])
        self.assertEqual(opening.lines[0].quantity, Decimal('0.000'))
        self.assertEqual([line.product_id for line in opening.recorded_lines], [product])

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
        for bad in ('-1', '1.0005', 'abc', 1.5, True, None, 'NaN', '100000000000', '1e3', '+5', ' ', '٣'):
            self.assertIn('quantity', self.errors(lines=[(uuid4(), bad)])['lines'][0], bad)


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
        body = {'name': name, 'sale_price': '10.00', 'category': 'finished'}
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
        """(movimientos del libro, 0): la segunda cifra se conserva para comparar antes/después con una tupla."""
        return StockMovementModel.objects.count(), 0

    def balance(self, product):
        return get_balance(self.company.id, UUID(product), UUID(self.warehouse))


class OpeningApiTests(StockApiTestCase):
    def test_confirming_creates_one_entry_per_line_and_the_balance(self):  # AC-01, AC-02
        flour, sugar = self.make_product('Harina'), self.make_product('Azúcar', self.kilo)
        response = self.open([line(flour, '10'), line(sugar, '2.5')])
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['reference'], 'Apertura 2026')
        self.assertEqual({entry['product_id']: entry['quantity'] for entry in body['lines']},
                         {flour: '10.0000', sugar: '2.5000'})
        movements = StockMovementModel.objects.filter(company_id=self.company.id)
        self.assertEqual(movements.count(), 2)
        self.assertEqual({(m.kind, m.source_type, m.reason, m.reference) for m in movements},
                         {('in', 'inventory_opening', 'Apertura de existencias', 'Apertura 2026')})
        self.assertEqual({m.user_name for m in movements}, {'ana'})
        self.assertEqual({m.source_id for m in movements}, {body['opening_id']})
        self.assertEqual((self.balance(flour), self.balance(sugar)), (Decimal('10'), Decimal('2.5')))

    def test_zero_quantity_creates_no_movement_and_does_not_consume_the_opening(self):  # EDGE-01
        product, other = self.make_product(), self.make_product('Sal')
        response = self.open([line(product, '0'), line(other, '3')])
        self.assertEqual(response.status_code, 201)
        self.assertEqual([entry['movement_id'] is None for entry in response.json()['lines']], [True, False])
        self.assertEqual(self.counts(), (1, 0))
        self.assertEqual(self.balance(product), Decimal('0'))
        self.assertFalse(has_history(self.company.id, UUID(product)))
        self.assertEqual(self.open([line(product, '5')]).status_code, 201)  # aún puede abrirse

    def test_an_opening_with_only_zero_lines_registers_nothing(self):  # EDGE-01
        response = self.open([line(self.make_product(), '0')])
        self.assertEqual((response.status_code, self.counts()), (201, (0, 0)))

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
        self.assertEqual(self.balance(product), Decimal('10'))

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

    def test_malformed_lines_answer_400_with_a_message_never_500(self):  # API-01, EDGE-05
        body = {'opening_id': str(uuid4()), 'warehouse_id': self.warehouse, 'movement_date': TODAY.isoformat(),
                'reference': 'x'}
        for bad in (5, 'abc', {'a': 1}, None, [5], [{'product_id': str(uuid4())}]):
            response = self.client.post(OPENINGS, {**body, 'lines': bad}, format='json')
            self.assertEqual(response.status_code, 400, bad)
            self.assertIn('lines', response.json(), bad)
        detail = self.client.post(OPENINGS, {**body, 'lines': 5}, format='json').json()['lines']
        self.assertEqual(list(detail), ['non_field_errors'])
        self.assertIn('lista', detail['non_field_errors'][0])
        self.assertEqual(self.counts(), (0, 0))

    def test_exponent_notation_is_rejected_like_the_ui_does(self):  # EDGE-02
        product = self.make_product()
        response = self.open([line(product, '1e3')])
        self.assertEqual(response.status_code, 400)
        self.assertIn('quantity', response.json()['lines'][0])

    def test_non_admin_members_get_403(self):  # EDGE-06
        product = self.make_product()
        member = make_admin(self.company, username='mario', role='member')
        other = APIClient()
        authenticate(other, member)
        body = {'opening_id': str(uuid4()), 'warehouse_id': self.warehouse, 'movement_date': TODAY.isoformat(),
                'reference': 'x', 'lines': [line(product)]}
        self.assertEqual(other.post(OPENINGS, body, format='json').status_code, 403)
        self.assertEqual(other.get(STOCK).status_code, 403)
        self.assertEqual(self.counts(), (0, 0))


class StockReadTests(StockApiTestCase):
    def test_stock_list_is_enriched_and_filterable_by_warehouse(self):  # AC-05, API-02
        product = self.make_product('Harina')
        other = self.client.post('/api/warehouses/', {'name': 'Tienda'}, format='json').json()['id']
        self.open([line(product, '7')])
        rows = self.client.get(STOCK, {'warehouse_id': self.warehouse}).json()['results']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['product_name'], 'Harina')
        self.assertEqual((rows[0]['quantity'], rows[0]['warehouse_name']), ('7.0000', 'Almacén principal'))
        self.assertEqual(rows[0]['unit'], {'abbreviation': 'u', 'allows_fractions': False})
        self.assertEqual(self.client.get(STOCK, {'warehouse_id': other}).json()['results'][0]['quantity'], '0.0000')
        self.assertEqual(self.client.get(STOCK).json()['count'], 2)
        self.assertEqual(self.client.get(STOCK, {'warehouse_id': 'nope'}).status_code, 400)

    def test_stock_is_isolated_between_companies(self):  # aislamiento
        self.open([line(self.make_product(), '7')])
        other = make_company('Empresa B')
        client = APIClient()
        authenticate(client, make_admin(other, username='beto'))
        set_enabled(other, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        self.assertEqual(client.get(STOCK).json()['count'], 0)

    def test_movements_of_the_opening_are_in_the_ledger_list(self):  # AC-05
        product = self.make_product()
        self.open([line(product, '4')], reference='Cierre de año')
        response = self.client.get('/api/stock-movements/', {'warehouse_id': self.warehouse, 'product_id': product})
        self.assertEqual(response.status_code, 200)
        rows = response.json()['results']
        self.assertEqual([(m['kind'], m['quantity_in'], m['reference']) for m in rows], [('in', '4.0000', 'Cierre de año')])
        self.assertEqual(rows[0]['source']['type'], 'inventory_opening')

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
        stock_history.register(has_history)
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
            'name': 'Harina', 'sale_price': '1.00', 'category': 'raw_material', 'tracks_stock': True, 'base_unit_id': unit}, format='json').json()['id']
        self.warehouse = client.get('/api/warehouses/').json()['results'][0]['id']

    def run_parallel(self, keys):
        barrier = Barrier(len(keys))
        outcomes = []

        def attempt(key):
            try:
                barrier.wait()
                use_case = RegisterOpening(
                    DjangoStockMovementRepository(self.company.id), DjangoWarehouseRepository(self.company.id),
                    CatalogProductDirectory(self.company.id))
                try:
                    outcome = use_case.execute(
                        opening_id=key, warehouse_id=UUID(self.warehouse), movement_date=TODAY, reference='Apertura',
                        lines=[(UUID(self.product), '5')], today=TODAY, user_name='carla')
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

    def test_two_keys_for_the_same_product_create_only_one(self):  # EDGE-03, INV-04
        self.assertEqual(self.run_parallel([uuid4(), uuid4()]), ['StockHistoryExists', 'created'])
        self.assertEqual(StockMovementModel.objects.filter(company_id=self.company.id).count(), 1)
