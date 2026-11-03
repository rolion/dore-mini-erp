"""PB-VAL-002: valoración de recepciones y consumos con costo promedio móvil histórico."""
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.costing.domain.costing import CostState, value_entry, value_exit
from modules.costing.domain.exceptions import MovementValuationRejected
from modules.costing.infrastructure.django.models import MovementValuationModel, ProductCostModel
from modules.inventory import services as inventory
from modules.inventory.infrastructure.django.models import StockMovementModel
from modules.inventory.tests.policy import set_negative_stock
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled
from modules.purchases.tests.test_receipt_api import ENABLED as PURCHASES_ENABLED
from modules.purchases.tests.test_receipt_api import ReceiptApiTestCase, purchase_url
from shared import stock_valuation

ENABLED = (*PURCHASES_ENABLED, 'costing')
MOVEMENTS = '/api/valuation/movements/'
COSTS = '/api/valuation/costs/'
ADJUSTMENTS = '/api/stock-adjustments/'
D = Decimal


class MovementValuationDomainTests(SimpleTestCase):
    def test_entry_at_purchase_price_updates_quantity_value_and_average(self):  # AC-01
        state = CostState(D('10'), D('50.00'))
        result = value_entry(state, D('4'), unit_cost=D('8.00'), cost_origin='purchase_price')
        self.assertEqual((result.value, result.unit_cost, result.average_before, result.average_after),
                         (D('32.00'), D('8.000000'), D('5.000000'), D('5.857143')))
        self.assertEqual(result.state_after, CostState(D('14'), D('82.00')))

    def test_exit_uses_the_current_average_and_empties_without_residue(self):  # AC-03, AC-04, INV-02
        state = CostState(D('3'), D('10.00'))
        first = value_exit(state, D('1'))
        self.assertEqual((first.unit_cost, first.value), (D('3.333333'), D('3.33')))
        rest = value_exit(first.state_after, D('2'))
        self.assertEqual((rest.value, rest.state_after), (D('6.67'), CostState(D('0'), D('0.00'))))

    def test_entry_without_value_is_required_and_zero_must_be_declared(self):  # AC-05
        state = CostState(D('1'), D('5.00'))
        for kwargs, code in (({}, 'valuation_required'), ({'total_value': '0'}, 'valuation_invalid'),
                             ({'total_value': '5', 'declared_zero': True}, 'valuation_invalid'),
                             ({'total_value': '1.234'}, 'valuation_invalid'),
                             ({'total_value': '-1'}, 'valuation_invalid')):
            with self.assertRaises(MovementValuationRejected) as ctx:
                value_entry(state, D('2'), cost_origin='manual_adjustment', **kwargs)
            self.assertEqual(ctx.exception.code, code, kwargs)
        zero = value_entry(state, D('2'), total_value='0', declared_zero=True, cost_origin='manual_adjustment')
        self.assertEqual((zero.value, zero.unit_cost), (D('0.00'), D('0.000000')))

    def test_exit_above_the_valued_quantity_is_blocked(self):
        with self.assertRaises(MovementValuationRejected) as ctx:
            value_exit(CostState(D('1'), D('5.00')), D('2'))
        self.assertEqual(ctx.exception.code, 'valuation_blocked')


class ValuedInventoryTestCase(ReceiptApiTestCase):
    """Empresa con 10 kg de harina adoptados en 50.00 BOB (promedio 5)."""

    def setUp(self):
        super().setUp()
        set_enabled(self.company, ENABLED)
        self.stock(self.flour, '10')
        response = self.client.post('/api/valuation/adopt/', {'adoption_id': str(uuid4()), 'lines': [{
            'product_id': str(self.flour.id), 'reconciled_quantity': '10.0000', 'total_value': '50.00'}]},
            format='json')
        self.assertEqual(response.status_code, 201, response.content)

    def stock(self, product, quantity):
        inventory.record_movement(
            self.company.id, product_id=product.id, warehouse_id=self.warehouse.id, kind='in',
            quantity=D(quantity), user_id=None, user_name='ana')

    def cost(self, product=None):
        row = ProductCostModel.objects.get(company_id=self.company.id, product_id=(product or self.flour).id)
        return row.quantity, row.total_value

    def snapshots(self, **filters):
        return MovementValuationModel.objects.filter(company_id=self.company.id, **filters).order_by('id')

    def ledger(self):
        return StockMovementModel.objects.filter(company_id=self.company.id).count()

    def receive_flour(self, quantity, price):
        purchase = self.confirmed_purchase([(self.flour, '100', price)])
        receipt = self.receive(purchase, [(self.item_id(purchase, self.flour), quantity)],
                               warehouse_id=str(self.warehouse.id))
        return purchase, receipt

    def out(self, quantity, order=None):
        inventory.record_outputs(
            self.company.id, warehouse_id=self.warehouse.id, lines=[(self.flour.id, D(quantity))],
            source_type='sales_order', source_id=str(order or uuid4()), user_id=None, user_name='ana')


class ReceiptValuationTests(ValuedInventoryTestCase):
    def test_partial_receipts_add_quantity_and_value_at_the_agreed_price(self):  # AC-01
        purchase = self.confirmed_purchase([(self.flour, '10', '8.00')])
        item = self.item_id(purchase, self.flour)
        first = self.receive(purchase, [(item, '4')], warehouse_id=str(self.warehouse.id))
        self.assertEqual(self.cost(), (D('14.0000'), D('82.00')))
        self.receive(purchase, [(item, '6')], warehouse_id=str(self.warehouse.id))
        self.assertEqual(self.cost(), (D('20.0000'), D('130.00')))
        body = self.client.get(MOVEMENTS, {'source_type': 'purchase_receipt', 'source_id': first['id']}).json()
        row = body['results'][0]
        self.assertEqual((row['kind'], row['quantity'], row['unit_cost'], row['value'], row['average_before'],
                          row['average_after'], row['cost_origin'], row['status']),
                         ('in', '4.0000', '8.000000', '32.00', '5.000000', '5.857143', 'purchase_price', 'valued'))

    def test_paying_the_supplier_does_not_revalue_stock(self):  # AC-02
        purchase, _ = self.receive_flour('4', '8.00')
        before = (self.snapshots().count(), self.cost())
        response = self.client.post(purchase_url(purchase['id'], 'payments/'), {
            'payment_id': str(uuid4()), 'amount': '20.00', 'payment_method': 'CASH',
            'payment_date': timezone.localdate().isoformat()}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual((self.snapshots().count(), self.cost()), before)

    def test_retrying_the_same_receipt_does_not_duplicate_the_valuation(self):  # AC-12
        purchase = self.confirmed_purchase([(self.flour, '10', '8.00')])
        item, receipt_id = self.item_id(purchase, self.flour), uuid4()
        self.receive(purchase, [(item, '4')], receipt_id=receipt_id, warehouse_id=str(self.warehouse.id))
        retry = self.client.post(purchase_url(purchase['id'], 'receipts/'), {
            'receipt_id': str(receipt_id), 'receipt_date': timezone.localdate().isoformat(),
            'lines': [{'item_id': item, 'quantity': '4'}], 'warehouse_id': str(self.warehouse.id)}, format='json')
        self.assertIn(retry.status_code, (200, 201), retry.content)
        self.assertEqual(self.snapshots(source_type='purchase_receipt').count(), 1)
        self.assertEqual(self.cost(), (D('14.0000'), D('82.00')))

    def test_reverting_a_receipt_without_later_movements_restores_the_cost(self):  # AC-09
        purchase, receipt = self.receive_flour('4', '8.00')
        response = self.client.post(purchase_url(purchase['id'], f'receipts/{receipt["id"]}/revert/'),
                                    {'reason': 'Devuelta al proveedor'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.cost(), (D('10.0000'), D('50.00')))
        counter = self.snapshots().last()
        self.assertEqual((counter.kind, counter.value, counter.cost_origin), ('out', D('32.00'), 'reversal_snapshot'))

    def test_reverting_a_receipt_is_blocked_when_a_later_consumption_used_its_cost(self):  # AC-09
        purchase, receipt = self.receive_flour('4', '8.00')
        self.out('2')
        before = (self.ledger(), self.snapshots().count(), self.cost())
        response = self.client.post(purchase_url(purchase['id'], f'receipts/{receipt["id"]}/revert/'),
                                    {'reason': 'Devuelta al proveedor'}, format='json')
        self.assertIn(response.status_code, (400, 409), response.content)
        self.assertIn('posteriores', str(response.json()))
        self.assertEqual((self.ledger(), self.snapshots().count(), self.cost()), before)  # AC-11

    def test_receipt_of_a_product_without_adoption_line_starts_from_zero(self):  # EDGE-03
        purchase = self.confirmed_purchase([(self.boxes, '5', '3.00')])
        self.receive(purchase, [(self.item_id(purchase, self.boxes), '5')], warehouse_id=str(self.warehouse.id))
        self.assertEqual(self.cost(self.boxes), (D('5.0000'), D('15.00')))

    def test_zero_price_receipt_is_valued_at_zero(self):  # EDGE-02
        purchase = self.confirmed_purchase([(self.flour, '10', '0.00')])
        self.receive(purchase, [(self.item_id(purchase, self.flour), '5')], warehouse_id=str(self.warehouse.id))
        self.assertEqual(self.cost(), (D('15.0000'), D('50.00')))


class ConsumptionValuationTests(ValuedInventoryTestCase):
    def test_exit_fixes_the_average_and_later_purchases_do_not_change_it(self):  # AC-03, INV-03
        order = uuid4()
        self.out('4', order)
        snapshot = self.snapshots(source_id=str(order)).get()
        self.assertEqual((snapshot.unit_cost, snapshot.value, snapshot.cost_origin),
                         (D('5.000000'), D('20.00'), 'average_at_exit'))
        self.receive_flour('10', '20.00')
        snapshot.refresh_from_db()
        self.assertEqual((snapshot.unit_cost, snapshot.value, snapshot.average_after), (D('5.000000'), D('20.00'), D('5.000000')))

    def test_exit_that_empties_the_product_takes_all_the_value(self):  # AC-04
        self.out('3')
        self.out('7')
        self.assertEqual(self.cost(), (D('0.0000'), D('0.00')))

    def test_negative_adjustment_consumes_the_current_value_without_asking_for_one(self):  # AC-06
        response = self.adjust('8')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.cost(), (D('8.0000'), D('40.00')))

    def adjust(self, counted, expected='10', **extra):
        return self.client.post(ADJUSTMENTS, {
            'adjustment_id': str(uuid4()), 'product_id': str(self.flour.id), 'warehouse_id': str(self.warehouse.id),
            'counted_quantity': counted, 'expected_system_quantity': expected, 'reason': 'Conteo', **extra},
            format='json')

    def test_positive_adjustment_requires_an_explicit_value(self):  # AC-05
        missing = self.adjust('12')
        self.assertEqual(missing.status_code, 400, missing.content)
        self.assertIn('total_value', missing.json())
        zero = self.adjust('12', total_value='0')
        self.assertEqual(zero.status_code, 400)
        self.assertEqual(self.ledger(), 1)  # solo el stock inicial: nada quedó registrado
        ok = self.adjust('12', total_value='11.00')
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(self.cost(), (D('12.0000'), D('61.00')))
        snapshot = self.snapshots().last()
        self.assertEqual((snapshot.cost_origin, snapshot.unit_cost), ('manual_adjustment', D('5.500000')))

    def test_positive_adjustment_with_declared_zero_cost(self):  # AC-05
        response = self.adjust('11', declared_zero=True)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.cost(), (D('11.0000'), D('50.00')))
        self.assertEqual(self.adjust('12', expected='11', total_value='3', declared_zero=True).status_code, 400)

    def test_negative_balance_is_blocked_even_if_the_policy_allows_it(self):  # AC-07, INV-04
        set_negative_stock(self.company, True)
        before = (self.ledger(), self.snapshots().count())
        with self.assertRaises(inventory.InsufficientStock):
            self.out('11')
        self.assertEqual((self.ledger(), self.snapshots().count()), before)
        self.assertFalse(inventory.allow_negative_stock(self.company.id))

    def test_retroactive_movement_is_blocked_with_an_explanation(self):  # AC-08, INV-05
        before = (self.ledger(), self.snapshots().count())
        with self.assertRaises(inventory.MovementConflict) as ctx:
            inventory.record_movement(
                self.company.id, product_id=self.flour.id, warehouse_id=self.warehouse.id, kind='out',
                quantity=D('1'), user_id=None, user_name='ana', source_type='sales_order', source_id='x',
                occurred_at=timezone.now() - timedelta(days=2))
        self.assertEqual(ctx.exception.code, 'valuation_blocked')
        self.assertIn('fecha anterior', str(ctx.exception))
        self.assertEqual((self.ledger(), self.snapshots().count()), before)

    def test_reversing_an_exit_re_enters_it_at_the_original_cost(self):  # AC-09
        self.out('4')
        movement = StockMovementModel.objects.filter(company_id=self.company.id, kind='out').get()
        self.receive_flour('10', '20.00')
        inventory.reverse_movement(self.company.id, movement.id, user_id=None, user_name='ana', reason='Error')
        entry = self.snapshots().last()
        self.assertEqual((entry.kind, entry.value, entry.cost_origin), ('in', D('20.00'), 'reversal_snapshot'))
        self.assertEqual(self.cost(), (D('20.0000'), D('250.00')))

    def test_snapshots_can_only_be_read_through_the_api(self):  # AC-15
        self.out('1')
        response = self.client.get(MOVEMENTS)
        self.assertEqual(response.status_code, 200)
        for method in ('post', 'put', 'patch', 'delete'):
            self.assertEqual(getattr(self.client, method)(MOVEMENTS, {}, format='json').status_code, 405, method)


class ValuationReadApiTests(ValuedInventoryTestCase):
    def test_filters_by_product_source_and_date(self):  # AC-14
        order = uuid4()
        self.out('2', order)
        self.receive_flour('3', '4.00')
        self.assertEqual(self.client.get(MOVEMENTS).json()['count'], 2)
        self.assertEqual(self.client.get(MOVEMENTS, {'source_type': 'sales_order', 'source_id': str(order)}).json()['count'], 1)
        self.assertEqual(self.client.get(MOVEMENTS, {'product_id': str(self.boxes.id)}).json()['count'], 0)
        today = timezone.localdate().isoformat()
        self.assertEqual(self.client.get(MOVEMENTS, {'date_from': today, 'date_to': today}).json()['count'], 2)
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.assertEqual(self.client.get(MOVEMENTS, {'date_from': tomorrow}).json()['count'], 0)
        label = self.client.get(MOVEMENTS, {'source_type': 'sales_order'}).json()['results'][0]['source_label']
        self.assertEqual(label, 'Pedido de venta')

    def test_invalid_filters_are_rejected_by_parameter(self):
        response = self.client.get(MOVEMENTS, {'date_from': 'ayer', 'product_id': 'x', 'source_id': '1'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'date_from', 'product_id', 'source_id'})

    def test_current_cost_per_product(self):  # AC-14
        self.out('4')
        body = self.client.get(COSTS).json()
        self.assertEqual(body, [{
            'product_id': str(self.flour.id), 'product_name': 'Harina', 'unit_abbreviation': 'kg',
            'quantity': '6.0000', 'total_value': '30.00', 'average_cost': '5.000000'}])


class ModuleAndIsolationTests(ValuedInventoryTestCase):
    def test_reads_are_forbidden_without_the_module_but_valuation_keeps_running(self):  # AC-13
        set_enabled(self.company, PURCHASES_ENABLED)
        self.assertEqual(self.client.get(MOVEMENTS).status_code, 403)
        self.assertEqual(self.client.get(COSTS).status_code, 403)
        self.out('2')
        self.assertEqual(self.cost(), (D('8.0000'), D('40.00')))
        self.assertEqual(self.snapshots().count(), 1)

    def test_other_company_does_not_see_or_share_valuations(self):  # AC-13
        self.out('2')
        other = make_company('Empresa B')
        client = APIClient()
        authenticate(client, make_admin(other, username='beto'))
        set_enabled(other, ENABLED)
        self.assertEqual(client.get(MOVEMENTS).json()['count'], 0)
        self.assertEqual(client.get(COSTS).json(), [])
        self.assertFalse(stock_valuation.is_valued(other.id))
        self.assertTrue(stock_valuation.is_valued(self.company.id))


class WithoutAdoptionTests(ReceiptApiTestCase):
    def test_company_without_adoption_behaves_as_before(self):  # AC-10
        set_enabled(self.company, ENABLED)
        purchase = self.confirmed_purchase([(self.flour, '10', '8.00')])
        self.receive(purchase, [(self.item_id(purchase, self.flour), '4')], warehouse_id=str(self.warehouse.id))
        self.assertEqual(MovementValuationModel.objects.count(), 0)
        self.assertEqual(ProductCostModel.objects.count(), 0)
        response = self.client.post(ADJUSTMENTS, {
            'adjustment_id': str(uuid4()), 'product_id': str(self.flour.id), 'warehouse_id': str(self.warehouse.id),
            'counted_quantity': '6', 'expected_system_quantity': '4', 'reason': 'Conteo'}, format='json')
        self.assertEqual(response.status_code, 201, response.content)


class AdoptionStateTests(ValuedInventoryTestCase):
    def test_adoption_initialises_the_running_cost_state(self):  # AC-16
        self.assertEqual(self.cost(), (D('10.0000'), D('50.00')))
        self.assertEqual(self.snapshots().count(), 0)


class SeedMigrationTests(ValuedInventoryTestCase):
    def test_data_migration_creates_the_state_for_existing_adoptions(self):  # AC-16
        import importlib

        from django.apps import apps

        ProductCostModel.objects.all().delete()
        seed = importlib.import_module(
            'modules.costing.migrations.0002_product_cost_and_movement_valuation').seed_cost_state
        seed(apps, None)
        seed(apps, None)  # idempotente
        self.assertEqual(self.cost(), (D('10.0000'), D('50.00')))
