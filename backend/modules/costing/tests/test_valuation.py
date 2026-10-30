"""PB-VAL-001: valoración inicial de inventario (adopción de un corte inmutable) detrás del módulo Costeo."""
from decimal import Decimal
from threading import Barrier, Thread
from uuid import UUID, uuid4

from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.costing.application.use_cases import AdoptValuation
from modules.costing.domain.exceptions import (
    AdoptionIdReused,
    ValuationAlreadyAdopted,
    ValuationValidationError,
)
from modules.costing.domain.valuation import ValuationAdoption, ValuationLine, compute_unit_cost, parse_lines
from modules.costing.infrastructure.adapters import InventoryCompanyStock
from modules.costing.infrastructure.django.models import ValuationAdoptionModel, ValuationLineModel
from modules.costing.infrastructure.django.repositories import DjangoAdoptionRepository
from modules.inventory import services as inventory
from modules.inventory.infrastructure.django.models import StockMovementModel
from modules.inventory.tests.policy import set_negative_stock
from modules.modularity.domain import modules as modules_domain
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled

TODAY = timezone.localdate()
VALUATION = '/api/valuation/'
PROPOSAL = '/api/valuation/proposal/'
ADOPT = '/api/valuation/adopt/'
ENABLED = [*DEFAULT_ENABLED_KEYS, 'inventory', 'costing']


def raw(product_id=None, quantity='10', value='50.00', zero=False, source=None):
    return {'product_id': product_id or uuid4(), 'reconciled_quantity': quantity, 'total_value': value,
            'declared_zero': zero, 'source': source}


class ValuationDomainTests(SimpleTestCase):
    def errors(self, **overrides):
        with self.assertRaises(ValuationValidationError) as ctx:
            parse_lines([raw(**overrides)])
        return ctx.exception.errors['lines'][0]

    def test_unit_cost_is_derived_with_six_decimals_half_up(self):  # AC-02, INV-02
        self.assertEqual(compute_unit_cost(Decimal('10.00'), Decimal('3.0000')), Decimal('3.333333'))
        self.assertEqual(compute_unit_cost(Decimal('20.00'), Decimal('3.0000')), Decimal('6.666667'))
        self.assertEqual(compute_unit_cost(Decimal('0.01'), Decimal('8.0000')), Decimal('0.001250'))

    def test_line_normalises_value_quantity_and_source(self):  # AC-02
        (line,) = parse_lines([raw(quantity='3', value='10', source='  Factura 7 ')])
        self.assertEqual((line.reconciled_quantity, line.total_value, line.unit_cost, line.source),
                         (Decimal('3.0000'), Decimal('10.00'), Decimal('3.333333'), 'Factura 7'))
        self.assertEqual(parse_lines([raw()])[0].source, 'Ingreso manual')

    def test_missing_value_is_pending_never_zero(self):  # AC-03, INV-03
        for missing in (None, '', '  '):
            self.assertIn('Pendiente', self.errors(value=missing)['total_value'][0])

    def test_zero_needs_an_explicit_declaration(self):  # AC-03, INV-03
        self.assertIn('declararse', self.errors(value='0')['total_value'][0])
        (line,) = parse_lines([raw(value='0', zero=True)])
        self.assertEqual((line.total_value, line.unit_cost, line.declared_zero),
                         (Decimal('0.00'), Decimal('0.000000'), True))
        (line,) = parse_lines([raw(value=None, zero=True)])
        self.assertEqual(line.total_value, Decimal('0.00'))

    def test_declared_zero_rejects_a_positive_value(self):  # INV-03
        self.assertIn('total_value', self.errors(value='5.00', zero=True))

    def test_invalid_values_are_rejected_per_line(self):  # EDGE-04, EDGE-05
        for value in ('abc', '-1', '1.234', '1e3', True, 1.5):
            self.assertIn('total_value', self.errors(value=value), repr(value))
        for quantity in ('0', 'x', '-2', '1.00001', None):
            self.assertIn('reconciled_quantity', self.errors(quantity=quantity), repr(quantity))

    def test_repeated_product_is_rejected(self):  # EDGE-05
        product = uuid4()
        with self.assertRaises(ValuationValidationError) as ctx:
            parse_lines([raw(product), raw(product)])
        self.assertEqual(ctx.exception.errors['lines'][0], {})
        self.assertIn('product_id', ctx.exception.errors['lines'][1])

    def test_adoption_has_no_mutators_and_compares_content(self):  # INV-01
        lines = parse_lines([raw(quantity='2', value='4.00')])
        adoption = ValuationAdoption.adopt(uuid4(), timezone.now(), None, 'ana', lines)
        self.assertTrue(adoption.same_content_as(lines))
        self.assertFalse(adoption.same_content_as(parse_lines([raw(lines[0].product_id, '2', '5.00')])))
        with self.assertRaises(Exception):
            adoption.method = 'otro'  # type: ignore[misc]
        with self.assertRaises(Exception):
            lines[0].total_value = Decimal('1')  # type: ignore[misc]

    def test_costing_module_requires_inventory_and_is_not_default(self):  # AC-08
        self.assertEqual(modules_domain.BY_KEY['costing'].requires, ('inventory',))
        self.assertNotIn('costing', modules_domain.DEFAULT_ENABLED_KEYS)
        self.assertIsInstance(ValuationLine, type)


class CostingApiTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.admin = make_admin(self.company, username='ana')
        authenticate(self.client, self.admin)
        set_enabled(self.company, ENABLED)
        self.unit = self.client.post(
            '/api/units/', {'name': 'Kilogramo', 'abbreviation': 'kg', 'allows_fractions': True},
            format='json').json()['id']
        self.warehouse = self.client.get('/api/warehouses/').json()['results'][0]['id']

    def make_product(self, name='Harina', client=None):
        response = (client or self.client).post('/api/products/', {
            'name': name, 'sale_price': '10.00', 'category': 'finished', 'tracks_stock': True,
            'base_unit_id': self.unit}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()['id']

    def open_stock(self, product, quantity='10', warehouse=None):
        response = self.client.post('/api/stock/openings/', {
            'opening_id': str(uuid4()), 'warehouse_id': warehouse or self.warehouse,
            'movement_date': TODAY.isoformat(), 'reference': 'Apertura', 'lines': [
                {'product_id': product, 'quantity': quantity}]}, format='json')
        self.assertEqual(response.status_code, 201, response.content)

    def line(self, product, quantity='10.0000', value='50.00', **extra):
        return {'product_id': product, 'reconciled_quantity': quantity, 'total_value': value, **extra}

    def adopt(self, lines, adoption_id=None, client=None):
        return (client or self.client).post(
            ADOPT, {'adoption_id': str(adoption_id or uuid4()), 'lines': lines}, format='json')

    def movements(self):
        return list(StockMovementModel.objects.order_by('id').values_list('id', 'quantity', 'kind'))


class AdoptionTests(CostingApiTestCase):
    def test_adopting_stores_one_cut_with_one_line_per_product_and_leaves_the_ledger_alone(self):  # AC-01, AC-02
        flour, sugar = self.make_product('Harina'), self.make_product('Azúcar')
        self.open_stock(flour, '3')
        self.open_stock(sugar, '4')
        before = self.movements()
        response = self.adopt([self.line(flour, '3.0000', '10.00'), self.line(sugar, '4.0000', '0', declared_zero=True,
                                                                              source='Conteo')])
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['status'], 'adopted')
        lines = {line['product_name']: line for line in body['adoption']['lines']}
        self.assertEqual((lines['Harina']['total_value'], lines['Harina']['unit_cost'], lines['Harina']['source']),
                         ('10.00', '3.333333', 'Ingreso manual'))
        self.assertEqual((lines['Azúcar']['total_value'], lines['Azúcar']['declared_zero'],
                          lines['Azúcar']['unit_abbreviation']), ('0.00', True, 'kg'))
        self.assertEqual(body['adoption']['method'], 'weighted_moving_average')
        self.assertEqual(body['adoption']['user_name'], 'ana')
        self.assertEqual(ValuationAdoptionModel.objects.count(), 1)
        self.assertEqual(ValuationLineModel.objects.count(), 2)
        self.assertEqual(self.movements(), before)  # AC-01 / INV-05
        read = self.client.get(VALUATION).json()
        self.assertEqual(read['status'], 'adopted')
        self.assertEqual(len(read['adoption']['lines']), 2)

    def test_status_is_not_adopted_before_the_cut(self):
        self.assertEqual(self.client.get(VALUATION).json(), {'status': 'not_adopted', 'adoption': None})

    def test_company_without_stock_can_adopt_with_no_lines(self):  # AC-07
        response = self.adopt([])
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['adoption']['lines'], [])

    def test_product_with_zero_balance_is_not_part_of_the_cut(self):  # EDGE-02
        product = self.make_product()
        self.open_stock(product, '5')
        inventory.record_movement(self.company.id, product_id=UUID(product), warehouse_id=UUID(self.warehouse),
                                  kind='out', quantity=Decimal('5'), user_id=None, user_name='ana')
        self.assertEqual(self.client.get(PROPOSAL).json()['lines'], [])
        self.assertEqual(self.adopt([]).status_code, 201)

    def test_pending_line_is_rejected_and_nothing_is_stored(self):  # AC-03
        product = self.make_product()
        self.open_stock(product)
        response = self.adopt([self.line(product, value=None)])
        self.assertEqual(response.status_code, 400)
        self.assertIn('Pendiente', response.json()['lines'][0]['total_value'][0])
        self.assertEqual(self.adopt([self.line(product, value='0')]).status_code, 400)
        self.assertEqual(ValuationAdoptionModel.objects.count(), 0)

    def test_shape_errors_are_reported_by_position(self):
        response = self.client.post(ADOPT, {'adoption_id': 'x', 'lines': [{'product_id': 'y'}]}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('adoption_id', response.json())

    def test_quantity_must_match_the_ledger(self):  # AC-05
        product = self.make_product()
        self.open_stock(product, '10')
        response = self.adopt([self.line(product, '9.0000')])
        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body['code'], 'stock_changed')
        self.assertEqual(body['lines'], [{'product_id': product, 'sent_quantity': '9.0000',
                                          'current_quantity': '10.0000'}])
        self.assertEqual(ValuationAdoptionModel.objects.count(), 0)

    def test_movement_after_the_proposal_invalidates_the_reconciliation(self):  # AC-05
        product = self.make_product()
        self.open_stock(product, '10')
        sent = self.client.get(PROPOSAL).json()['lines'][0]['reconciled_quantity']
        inventory.record_movement(self.company.id, product_id=UUID(product), warehouse_id=UUID(self.warehouse),
                                  kind='in', quantity=Decimal('1'), user_id=None, user_name='ana')
        self.assertEqual(self.adopt([self.line(product, sent)]).json()['code'], 'stock_changed')

    def test_missing_or_extra_products_are_a_difference(self):  # AC-05
        product, other = self.make_product(), self.make_product('Otro')
        self.open_stock(product, '10')
        missing = self.adopt([])
        self.assertEqual((missing.status_code, missing.json()['code']), (409, 'stock_changed'))
        extra = self.adopt([self.line(product), self.line(other, '1.0000')])
        self.assertEqual((extra.status_code, extra.json()['code']), (409, 'stock_changed'))

    def test_negative_stock_blocks_the_adoption(self):  # AC-04
        set_negative_stock(self.company, True)
        product = self.make_product()
        inventory.record_movement(self.company.id, product_id=UUID(product), warehouse_id=UUID(self.warehouse),
                                  kind='out', quantity=Decimal('2'), user_id=None, user_name='ana')
        proposal = self.client.get(PROPOSAL).json()
        self.assertEqual(proposal['lines'], [])
        self.assertEqual([(b['product_id'], b['quantity']) for b in proposal['blockers']], [(product, '-2.0000')])
        response = self.adopt([])
        self.assertEqual((response.status_code, response.json()['code']), (409, 'negative_stock'))
        self.assertEqual(response.json()['blockers'][0]['warehouse_name'], proposal['blockers'][0]['warehouse_name'])
        self.assertEqual(ValuationAdoptionModel.objects.count(), 0)

    def test_proposal_sums_warehouses_and_keeps_the_breakdown(self):
        product = self.make_product()
        second = self.client.post('/api/warehouses/', {'name': 'Tienda'}, format='json').json()['id']
        self.open_stock(product, '10')
        self.open_stock(product, '2.5', warehouse=second)
        (line,) = self.client.get(PROPOSAL).json()['lines']
        self.assertEqual((line['product_name'], line['reconciled_quantity'], line['unit_abbreviation']),
                         ('Harina', '12.5000', 'kg'))
        self.assertEqual(sorted(w['quantity'] for w in line['warehouses']), ['10.0000', '2.5000'])

    def test_same_key_and_content_is_a_replay_and_other_cases_conflict(self):  # AC-06
        product = self.make_product()
        self.open_stock(product)
        key = uuid4()
        first = self.adopt([self.line(product)], key)
        again = self.adopt([self.line(product)], key)
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(first.json(), again.json())
        reused = self.adopt([self.line(product, value='99.00')], key)
        self.assertEqual((reused.status_code, reused.json()['code']), (409, 'adoption_id_reused'))
        other = self.adopt([self.line(product)])
        self.assertEqual((other.status_code, other.json()['code']), (409, 'valuation_already_adopted'))
        self.assertEqual(ValuationAdoptionModel.objects.count(), 1)

    def test_there_is_no_way_to_edit_or_delete_an_adoption(self):  # INV-01
        self.adopt([])
        for method in ('put', 'patch', 'delete'):
            self.assertEqual(getattr(self.client, method)(VALUATION, {}, format='json').status_code, 405)


class ModuleAndIsolationTests(CostingApiTestCase):
    def test_every_route_needs_the_costing_module(self):  # AC-08
        set_enabled(self.company, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        for method, path in (('get', VALUATION), ('get', PROPOSAL), ('post', ADOPT)):
            response = getattr(self.client, method)(path, {}, format='json')
            self.assertEqual(response.status_code, 403, path)
            self.assertEqual(response.json(), {'detail': 'Módulo no habilitado', 'code': 'module_disabled',
                                               'module': 'costing'})

    def test_costing_cannot_be_enabled_without_inventory(self):  # AC-08
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)
        response = self.client.post('/api/modules/costing/enable/')
        self.assertEqual(response.status_code, 409, response.content)

    def test_requires_authentication(self):
        self.client.credentials()
        self.assertIn(self.client.get(VALUATION).status_code, (401, 403))

    def test_another_company_does_not_see_or_block_the_adoption(self):  # AC-09
        product = self.make_product()
        self.open_stock(product)
        self.assertEqual(self.adopt([self.line(product)]).status_code, 201)
        other = make_company('Empresa B')
        other_client = APIClient()
        authenticate(other_client, make_admin(other, username='beto'))
        set_enabled(other, ENABLED)
        self.assertEqual(other_client.get(VALUATION).json()['status'], 'not_adopted')
        self.assertEqual(other_client.get(PROPOSAL).json(), {'lines': [], 'blockers': []})
        self.assertEqual(self.adopt([], client=other_client).status_code, 201)
        self.assertEqual(ValuationAdoptionModel.objects.count(), 2)

    def test_company_sent_by_the_client_is_ignored(self):  # AC-09, INV-06
        other = make_company('Empresa B')
        response = self.client.post(
            ADOPT, {'adoption_id': str(uuid4()), 'company_id': str(other.id), 'lines': []}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ValuationAdoptionModel.objects.get().company_id, self.company.id)


class ConcurrentAdoptionTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('Empresa C')
        client = APIClient()
        authenticate(client, make_admin(self.company, username='carla'))
        set_enabled(self.company, ENABLED)
        client.get('/api/warehouses/')  # siembra el almacén predeterminado

    def run_parallel(self, keys):
        barrier = Barrier(len(keys))
        outcomes = []

        def attempt(key):
            try:
                barrier.wait()
                use_case = AdoptValuation(DjangoAdoptionRepository(self.company.id),
                                          InventoryCompanyStock(self.company.id))
                try:
                    outcome = use_case.execute(adoption_id=key, raw_lines=[], user_id=None, user_name='carla',
                                               now=timezone.now())
                    outcomes.append('replayed' if outcome.replayed else 'created')
                except (ValuationAlreadyAdopted, AdoptionIdReused) as exc:
                    outcomes.append(type(exc).__name__)
            finally:
                connection.close()

        threads = [Thread(target=attempt, args=(key,)) for key in keys]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return sorted(outcomes)

    def test_double_submit_with_the_same_key_adopts_once(self):  # AC-06
        key = uuid4()
        self.assertEqual(self.run_parallel([key, key]), ['created', 'replayed'])
        self.assertEqual(ValuationAdoptionModel.objects.filter(company_id=self.company.id).count(), 1)

    def test_two_different_keys_adopt_once(self):  # AC-06, INV-01
        self.assertEqual(self.run_parallel([uuid4(), uuid4()]), ['ValuationAlreadyAdopted', 'created'])
        self.assertEqual(ValuationAdoptionModel.objects.filter(company_id=self.company.id).count(), 1)
