"""PB-INV-006: ajustes de existencias con motivo (diferencia, saldo cambiado, idempotencia y lecturas)."""
from decimal import Decimal
from threading import Barrier, Thread
from uuid import UUID, uuid4

from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase
from rest_framework.test import APIClient

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.inventory.application.adjustment_use_cases import ConfirmAdjustment
from modules.inventory.domain.adjustment import StockAdjustment
from modules.inventory.domain.exceptions import AdjustmentValidationError, NoDifference
from modules.inventory.infrastructure.adapters import CatalogProductDirectory
from modules.inventory.infrastructure.django.adjustment_repository import DjangoStockAdjustmentRepository
from modules.inventory.infrastructure.django.models import StockAdjustmentModel, StockMovementModel
from modules.inventory.infrastructure.django.movement_repository import DjangoStockMovementRepository
from modules.inventory.infrastructure.django.repositories import DjangoWarehouseRepository
from modules.inventory.domain.adjustment import (
    validate_counted_quantity,
    validate_expected_balance,
    validate_reason,
)
from modules.inventory.services import get_balance
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled

from .test_stock import StockApiTestCase, line

ADJUSTMENTS = '/api/stock-adjustments/'


class AdjustmentDomainTests(SimpleTestCase):
    def create(self, system='10', counted='7'):
        return StockAdjustment.create(
            adjustment_id=uuid4(), product_id=uuid4(), warehouse_id=uuid4(), system_quantity=Decimal(system),
            counted_quantity=Decimal(counted), reason='Conteo', user_id=None, user_name='ana')

    def test_difference_and_direction_are_calculated(self):  # INV-03, AC-01
        out, entry = self.create('10', '7'), self.create('2', '5.5')
        self.assertEqual((out.difference, out.kind.value), (Decimal('-3'), 'out'))
        self.assertEqual((entry.difference, entry.kind.value), (Decimal('3.5'), 'in'))
        self.assertTrue(out.reference.startswith('AJ-'))

    def test_negative_system_balance_gives_an_entry(self):  # EDGE-04
        self.assertEqual(self.create('-2', '3').difference, Decimal('5'))

    def test_zero_difference_is_not_an_adjustment(self):  # INV-04, AC-04
        with self.assertRaises(NoDifference):
            self.create('4', '4.000')

    def test_counted_quantity_rules(self):  # INV-05, EDGE-02
        self.assertEqual(validate_counted_quantity(' 2.5 '), Decimal('2.500'))
        for bad in ('-1', '1.0005', 'abc', 1.5, True, None, 'NaN', '1e3', '+5', ''):
            with self.assertRaises(AdjustmentValidationError, msg=repr(bad)) as ctx:
                validate_counted_quantity(bad)
            self.assertIn('counted_quantity', ctx.exception.errors)

    def test_expected_balance_may_be_negative_but_not_a_float(self):  # EDGE-04
        self.assertEqual(validate_expected_balance('-2.5'), Decimal('-2.5000'))
        with self.assertRaises(AdjustmentValidationError):
            validate_expected_balance(1.5)

    def test_reason_is_required_and_limited(self):  # INV-05
        self.assertEqual(validate_reason('  Rotura  '), 'Rotura')
        for bad in ('', '   ', None, 'x' * 201):
            with self.assertRaises(AdjustmentValidationError, msg=repr(bad)):
                validate_reason(bad)


class AdjustmentApiTests(StockApiTestCase):
    def adjust(self, product, counted, expected, key=None, reason='Conteo físico', warehouse=None, client=None):
        body = {'adjustment_id': str(key or uuid4()), 'product_id': str(product),
                'warehouse_id': warehouse or self.warehouse, 'counted_quantity': counted,
                'expected_system_quantity': expected, 'reason': reason}
        return (client or self.client).post(ADJUSTMENTS, body, format='json')

    def stocked(self, quantity='10', **kwargs):
        product = self.make_product(**kwargs)
        self.assertEqual(self.open([line(product, quantity)]).status_code, 201)
        return product

    def test_confirming_a_lower_count_creates_an_adjustment_out(self):  # AC-01, AC-02, INV-07
        product = self.stocked('10')
        response = self.adjust(product, '7', '10')
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual((body['system_quantity'], body['counted_quantity'], body['difference'], body['kind']),
                         ('10.0000', '7.0000', '-3.0000', 'out'))
        self.assertEqual((body['status'], body['reason'], body['user']['name']), ('confirmed', 'Conteo físico', 'ana'))
        movement = StockMovementModel.objects.get(pk=body['movement']['id'])
        self.assertEqual((movement.kind, movement.quantity, movement.source_type, movement.source_id,
                          movement.reason, movement.reference),
                         ('out', Decimal('3'), 'inventory_adjustment', body['id'], 'Conteo físico', body['reference']))
        self.assertEqual(self.balance(product), Decimal('7'))
        self.assertEqual(StockMovementModel.objects.filter(company_id=self.company.id).count(), 2)  # no sobrescribe

    def test_confirming_a_higher_count_creates_an_adjustment_in(self):  # AC-02
        product = self.stocked('4', unit=self.kilo)
        body = self.adjust(product, '6.5', '4').json()
        self.assertEqual((body['difference'], body['kind']), ('2.5000', 'in'))
        self.assertEqual(self.balance(product), Decimal('6.5'))

    def test_a_product_without_history_can_be_adjusted(self):  # supuesto del plan
        product = self.make_product()
        self.assertEqual(self.adjust(product, '3', '0').status_code, 201)
        self.assertEqual(self.balance(product), Decimal('3'))

    def test_zero_difference_registers_nothing(self):  # AC-04, INV-04
        product = self.stocked('10')
        response = self.adjust(product, '10', '10')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'no_difference'))
        self.assertEqual((StockAdjustmentModel.objects.count(), StockMovementModel.objects.count()), (0, 1))

    def test_changed_balance_requires_reviewing_and_registers_nothing(self):  # AC-03, INV-06
        product = self.stocked('10')
        first = self.adjust(product, '7', '10')
        self.assertEqual(first.status_code, 201)  # el saldo pasó a 7
        response = self.adjust(product, '12', '10')
        self.assertEqual(response.status_code, 409)
        self.assertEqual((response.json()['code'], response.json()['current_balance']), ('balance_changed', '7.0000'))
        self.assertEqual(StockAdjustmentModel.objects.count(), 1)
        self.assertEqual(self.adjust(product, '12', '7').status_code, 201)  # reconfirmar con el saldo nuevo
        self.assertEqual(self.balance(product), Decimal('12'))

    def test_retrying_the_same_key_returns_the_original_even_if_the_balance_moved(self):  # AC-07, INV-08
        product = self.stocked('10')
        key = uuid4()
        first = self.adjust(product, '7', '10', key=key)
        again = self.adjust(product, '7', '10', key=key)
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(again.json(), first.json())
        self.assertEqual((StockAdjustmentModel.objects.count(), StockMovementModel.objects.count()), (1, 2))

    def test_same_key_with_other_data_is_a_conflict(self):  # INV-08
        product = self.stocked('10')
        key = uuid4()
        self.adjust(product, '7', '10', key=key)
        response = self.adjust(product, '6', '10', key=key)
        self.assertEqual((response.status_code, response.json()['code']), (409, 'adjustment_id_reused'))

    def test_validation_errors_by_field(self):  # AC-01, INV-05, EDGE-02, EDGE-03
        product = self.stocked('10')
        untracked = self.make_product('Servicio', tracks=False)
        cases = [
            (self.adjust(product, '-1', '10'), 'counted_quantity'),
            (self.adjust(product, '1.5', '10'), 'counted_quantity'),  # unidad entera
            (self.adjust(product, '7', '10', reason='   '), 'reason'),
            (self.adjust(product, '7', 'x'), 'expected_system_quantity'),
            (self.adjust(untracked, '1', '0'), 'product_id'),
            (self.adjust(uuid4(), '1', '0'), 'product_id'),
        ]
        for response, field in cases:
            self.assertEqual(response.status_code, 400, response.content)
            self.assertIn(field, response.json())
        self.assertEqual(StockAdjustmentModel.objects.count(), 0)

    def test_inactive_warehouse_is_rejected(self):  # EDGE-03
        product = self.make_product()
        other = self.client.post('/api/warehouses/', {'name': 'Tienda'}, format='json').json()['id']
        self.client.post(f'/api/warehouses/{other}/deactivate/')
        response = self.adjust(product, '3', '0', warehouse=other)
        self.assertEqual(response.status_code, 400)
        self.assertIn('warehouse_id', response.json())

    def test_list_detail_and_filters(self):  # AC-05, AC-06
        flour, sugar = self.stocked('10', name='Harina'), self.stocked('5', name='Azúcar')
        first = self.adjust(flour, '7', '10').json()
        self.adjust(sugar, '6', '5')
        rows = self.client.get(ADJUSTMENTS).json()
        self.assertEqual(rows['count'], 2)
        self.assertEqual(set(rows['results'][0]), {
            'id', 'reference', 'created_at', 'product', 'warehouse', 'system_quantity', 'counted_quantity',
            'difference', 'kind', 'unit', 'user', 'status'})
        self.assertEqual(rows['results'][0]['product']['name'], 'Azúcar')
        by_product = self.client.get(ADJUSTMENTS, {'product_id': flour}).json()
        self.assertEqual([r['id'] for r in by_product['results']], [first['id']])
        self.assertEqual(self.client.get(ADJUSTMENTS, {'warehouse_id': str(uuid4())}).json()['count'], 0)
        self.assertEqual(self.client.get(ADJUSTMENTS, {'date_from': '2999-01-01'}).json()['count'], 0)
        detail = self.client.get(f'{ADJUSTMENTS}{first["id"]}/').json()
        self.assertEqual((detail['reason'], detail['id'], detail['unit']['abbreviation']),
                         ('Conteo físico', first['id'], 'u'))
        self.assertEqual(self.client.get(ADJUSTMENTS, {'date_from': 'hoy'}).status_code, 400)
        self.assertEqual(self.client.get(ADJUSTMENTS, {'date_from': '2026-02-01', 'date_to': '2026-01-01'}
                                         ).status_code, 400)

    def test_status_follows_the_linked_movement(self):  # AC-05 (estado revertido)
        from modules.inventory.services import reverse_movement
        product = self.stocked('10')
        body = self.adjust(product, '7', '10').json()
        reverse_movement(self.company.id, UUID(body['movement']['id']), user_id=None, user_name='ana')
        self.assertEqual(self.client.get(f'{ADJUSTMENTS}{body["id"]}/').json()['status'], 'reversed')
        self.assertEqual(self.client.get(ADJUSTMENTS).json()['results'][0]['status'], 'reversed')

    def test_balance_endpoint(self):  # API-02
        product = self.stocked('10')
        body = self.client.get(f'{ADJUSTMENTS}balance/', {'product_id': product, 'warehouse_id': self.warehouse}).json()
        self.assertEqual((body['system_quantity'], body['unit']['abbreviation']), ('10.0000', 'u'))
        fresh = self.make_product('Sal')
        self.assertEqual(self.client.get(f'{ADJUSTMENTS}balance/', {
            'product_id': fresh, 'warehouse_id': self.warehouse}).json()['system_quantity'], '0.0000')
        self.assertEqual(self.client.get(f'{ADJUSTMENTS}balance/', {'product_id': product}).status_code, 400)
        self.assertEqual(self.client.get(f'{ADJUSTMENTS}balance/', {
            'product_id': str(uuid4()), 'warehouse_id': self.warehouse}).status_code, 404)

    def test_adjustments_are_read_only_after_creation(self):  # INV-02
        product = self.stocked('10')
        body = self.adjust(product, '7', '10').json()
        url = f'{ADJUSTMENTS}{body["id"]}/'
        for method in (self.client.put, self.client.patch, self.client.delete, self.client.post):
            self.assertEqual(method(url, {}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(ADJUSTMENTS).status_code, 405)

    def test_company_isolation_and_permissions(self):  # INV-09, autorización
        product = self.stocked('10')
        body = self.adjust(product, '7', '10').json()
        other = make_company('Empresa B')
        client = APIClient()
        authenticate(client, make_admin(other, username='beto'))
        set_enabled(other, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        self.assertEqual(client.get(f'{ADJUSTMENTS}{body["id"]}/').status_code, 404)
        self.assertEqual(client.get(ADJUSTMENTS).json()['count'], 0)
        self.assertEqual(self.adjust(product, '1', '10', client=client).status_code, 400)  # producto ajeno
        self.assertEqual(self.adjust(product, '1', '10', warehouse=str(uuid4())).status_code, 404)
        member = APIClient()
        authenticate(member, make_admin(self.company, username='mario', role='member'))
        self.assertEqual(self.adjust(product, '1', '7', client=member).status_code, 403)
        self.assertEqual(member.get(ADJUSTMENTS).status_code, 403)
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)
        self.assertEqual(self.client.get(ADJUSTMENTS).status_code, 403)


class ConcurrentAdjustmentTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('Empresa C')
        admin = make_admin(self.company, username='carla')
        client = APIClient()
        authenticate(client, admin)
        set_enabled(self.company, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        unit = client.post('/api/units/', {'name': 'Unidad', 'abbreviation': 'u'}, format='json').json()['id']
        self.product = UUID(client.post('/api/products/', {
            'name': 'Harina', 'sale_price': '1.00', 'tracks_stock': True, 'base_unit_id': unit},
            format='json').json()['id'])
        self.warehouse = UUID(client.get('/api/warehouses/').json()['results'][0]['id'])
        client.post('/api/stock/openings/', {
            'opening_id': str(uuid4()), 'warehouse_id': str(self.warehouse), 'movement_date': '2020-01-01',
            'reference': 'Apertura', 'lines': [{'product_id': str(self.product), 'quantity': '10'}]}, format='json')

    def run_parallel(self, attempts):
        """`attempts`: lista de (clave, cantidad contada); todos esperan saldo 10."""
        barrier = Barrier(len(attempts))
        outcomes = []

        def attempt(key, counted):
            try:
                barrier.wait()
                use_case = ConfirmAdjustment(
                    DjangoStockMovementRepository(self.company.id), DjangoStockAdjustmentRepository(self.company.id),
                    DjangoWarehouseRepository(self.company.id), CatalogProductDirectory(self.company.id))
                try:
                    _, created = use_case.execute(
                        adjustment_id=key, product_id=self.product, warehouse_id=self.warehouse,
                        counted_quantity=counted, expected_system_quantity='10', reason='Conteo', user_id=None,
                        user_name='carla')
                    outcomes.append('created' if created else 'replayed')
                except Exception as exc:  # noqa: BLE001 - se reporta el tipo para la aserción
                    outcomes.append(type(exc).__name__)
            finally:
                connection.close()

        threads = [Thread(target=attempt, args=args) for args in attempts]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return sorted(outcomes)

    def test_double_submit_with_the_same_key_creates_one_adjustment(self):  # AC-07, EDGE-01
        key = uuid4()
        self.assertEqual(self.run_parallel([(key, '7'), (key, '7')]), ['created', 'replayed'])
        self.assertEqual(StockAdjustmentModel.objects.count(), 1)
        self.assertEqual(get_balance(self.company.id, self.product, self.warehouse), Decimal('7'))

    def test_two_counts_from_the_same_balance_only_one_applies(self):  # AC-03, EDGE-01
        self.assertEqual(self.run_parallel([(uuid4(), '7'), (uuid4(), '5')]), ['BalanceChanged', 'created'])
        self.assertEqual(StockAdjustmentModel.objects.count(), 1)
