"""PB-INV-004: movimientos trazables de inventario."""
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from threading import Barrier, Thread
from uuid import uuid4

from django.db import connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.catalog.infrastructure.django.models import ProductModel, UnitModel
from modules.inventory import services as inventory
from modules.inventory.domain.exceptions import MovementConflict, MovementValidationError
from modules.inventory.domain.movement import MovementKind, MovementSource, MovementStatus, StockMovement
from modules.inventory.infrastructure.django.models import StockMovementModel, WarehouseModel
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled
from shared import stock_history

from .policy import set_negative_stock

URL = '/api/stock-movements/'
WHEN = datetime(2026, 10, 20, 15, 30, tzinfo=dt_timezone.utc)


def make_product(company, name='Arroz', tracks_stock=True, allows_fractions=True, abbreviation='kg'):
    unit, _ = UnitModel.objects.get_or_create(
        company_id=company.id, abbreviation=abbreviation,
        defaults={'name': f'Unidad {abbreviation}', 'allows_fractions': allows_fractions})
    return ProductModel.objects.create(
        company_id=company.id, name=name, sale_price=Decimal('10.00'), tracks_stock=tracks_stock,
        base_unit=unit if tracks_stock else None)


def make_warehouse(company, name='Central'):
    return WarehouseModel.objects.create(company_id=company.id, name=name)


class MovementDomainTests(SimpleTestCase):
    def record(self, **overrides):
        values = dict(product_id=uuid4(), warehouse_id=uuid4(), kind=MovementKind.IN, quantity='5',
                      occurred_at=WHEN, user_id=uuid4(), user_name='ana')
        values.update(overrides)
        return StockMovement.record(**values)

    def test_quantity_must_be_a_positive_decimal(self):  # INV-01
        for bad in (0, -1, 'x', 1.5, '1.00001'):
            with self.assertRaises(MovementValidationError, msg=repr(bad)):
                self.record(quantity=bad)
        self.assertEqual(self.record(quantity='2.5').quantity, Decimal('2.5000'))

    def test_unknown_source_type_is_rejected(self):  # INV-01
        with self.assertRaises(MovementValidationError):
            MovementSource('factura', '1')

    def test_reverse_returns_opposite_linked_counter_movement(self):  # INV-07
        original = self.record()
        counter = original.reverse(occurred_at=WHEN, user_id=None, user_name='ana', reason='Corrección')
        self.assertEqual(original.status, MovementStatus.REVERSED)
        self.assertEqual((counter.kind, counter.quantity, counter.reverses_id),
                         (MovementKind.OUT, original.quantity, original.id))
        self.assertIsNone(counter.source)

    def test_reverse_twice_or_a_counter_movement_fails(self):  # INV-07
        original = self.record()
        counter = original.reverse(occurred_at=WHEN, user_id=None, user_name='ana', reason='Corrección')
        with self.assertRaises(MovementConflict) as ctx:
            original.reverse(occurred_at=WHEN, user_id=None, user_name='ana', reason='Corrección')
        self.assertEqual(ctx.exception.code, 'already_reversed')
        with self.assertRaises(MovementConflict):
            counter.reverse(occurred_at=WHEN, user_id=None, user_name='ana', reason='Corrección')


class LedgerTestCase(TestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.product = make_product(self.company)
        self.warehouse = make_warehouse(self.company)

    def record(self, kind='in', quantity='10', **extra):
        values = dict(product_id=self.product.id, warehouse_id=self.warehouse.id, kind=kind,
                      quantity=Decimal(quantity), user_id=None, user_name='ana', occurred_at=WHEN)
        values.update(extra)
        return inventory.record_movement(self.company.id, **values)

    def balance(self):
        return inventory.get_balance(self.company.id, self.product.id, self.warehouse.id)


class RecordMovementTests(LedgerTestCase):
    def test_movement_stores_all_required_fields(self):  # AC-01
        movement, created = self.record(reference='PV-1', source_type='sales_order', source_id='42')
        self.assertTrue(created)
        row = StockMovementModel.objects.get(pk=movement.id)
        self.assertEqual(
            (row.company_id, row.product_id, row.warehouse_id, row.kind, row.quantity, row.occurred_at,
             row.user_name, row.source_type, row.source_id, row.status),
            (self.company.id, self.product.id, self.warehouse.id, 'in', Decimal('10.0000'), WHEN,
             'ana', 'sales_order', '42', 'confirmed'))

    def test_balance_is_entries_minus_exits(self):  # AC-02
        self.record('in', '10')
        self.record('out', '3.5')
        self.record('in', '1')
        self.assertEqual(self.balance(), Decimal('7.5'))

    def test_exit_without_enough_balance_is_rejected_unless_allowed(self):  # INV-05
        self.record('in', '2')
        with self.assertRaises(MovementConflict) as ctx:
            self.record('out', '3')
        self.assertEqual(ctx.exception.code, 'insufficient_stock')
        set_negative_stock(self.company, True)
        self.record('out', '3')
        self.assertEqual(self.balance(), Decimal('-1'))

    def test_same_source_operation_is_recorded_once(self):  # AC-03
        first, created_first = self.record(source_type='sales_order', source_id='42')
        again, created_again = self.record(source_type='sales_order', source_id='42')
        self.assertEqual((created_first, created_again, first.id), (True, False, again.id))
        self.assertEqual(StockMovementModel.objects.count(), 1)
        self.assertEqual(self.balance(), Decimal('10'))

    def test_retry_with_other_quantity_is_a_conflict(self):  # INV-03
        self.record(source_type='sales_order', source_id='42')
        with self.assertRaises(MovementConflict) as ctx:
            self.record(quantity='11', source_type='sales_order', source_id='42')
        self.assertEqual(ctx.exception.code, 'source_operation_mismatch')

    def test_retry_returns_existing_even_if_balance_changed(self):  # AC-03
        self.record('in', '5')
        self.record('out', '5', source_type='sales_order', source_id='7')
        _, created = self.record('out', '5', source_type='sales_order', source_id='7')
        self.assertFalse(created)

    def test_other_line_product_or_kind_of_same_document_is_a_different_operation(self):  # INV-03
        self.record('in', '10')
        self.record('out', '1', source_type='sales_order', source_id='42', source_line='1')
        _, created = self.record('out', '1', source_type='sales_order', source_id='42', source_line='2')
        self.assertTrue(created)
        _, created = self.record('in', '1', source_type='sales_order', source_id='42', source_line='1')
        self.assertTrue(created)

    def test_validations(self):  # INV-06, EDGE-02
        untracked = make_product(self.company, 'Servicio', tracks_stock=False)
        whole = make_product(self.company, 'Caja', allows_fractions=False, abbreviation='cj')
        inactive = make_warehouse(self.company, 'Cerrado')
        inactive.active = False
        inactive.save()
        cases = [
            ({'product_id': untracked.id}, 'product_id'),
            ({'product_id': uuid4()}, 'product_id'),
            ({'product_id': whole.id, 'quantity': '1.5'}, 'quantity'),
            ({'warehouse_id': inactive.id}, 'warehouse_id'),
            ({'warehouse_id': uuid4()}, 'warehouse_id'),
            ({'quantity': '0'}, 'quantity'),
        ]
        for extra, field in cases:
            with self.assertRaises(MovementValidationError, msg=field) as ctx:
                self.record(**extra)
            self.assertIn(field, ctx.exception.errors)

    def test_other_company_data_is_not_visible(self):  # INV-08
        other = make_company('Empresa B')
        with self.assertRaises(MovementValidationError):
            inventory.record_movement(
                other.id, product_id=self.product.id, warehouse_id=self.warehouse.id, kind='in',
                quantity=Decimal('1'), user_id=None, user_name='bea')
        self.record()
        self.assertEqual(inventory.get_balance(other.id, self.product.id, self.warehouse.id), Decimal('0'))


class ReverseMovementTests(LedgerTestCase):
    def test_reverse_marks_original_and_balance_returns(self):  # INV-07
        entry, _ = self.record('in', '10')
        counter = inventory.reverse_movement(self.company.id, entry.id, user_id=None, user_name='ana', reason='Corrección')
        self.assertEqual((counter.kind, counter.reverses_id), ('out', entry.id))
        self.assertEqual(StockMovementModel.objects.get(pk=entry.id).status, 'reversed')
        self.assertEqual(self.balance(), Decimal('0'))

    def test_reverse_twice_is_409(self):  # EDGE-03
        entry, _ = self.record('in', '10')
        inventory.reverse_movement(self.company.id, entry.id, user_id=None, user_name='ana', reason='Corrección')
        with self.assertRaises(MovementConflict) as ctx:
            inventory.reverse_movement(self.company.id, entry.id, user_id=None, user_name='ana', reason='Corrección')
        self.assertEqual(ctx.exception.code, 'already_reversed')

    def test_reverse_an_entry_already_consumed_needs_balance(self):  # INV-05
        entry, _ = self.record('in', '10')
        self.record('out', '8')
        with self.assertRaises(MovementConflict) as ctx:
            inventory.reverse_movement(self.company.id, entry.id, user_id=None, user_name='ana', reason='Corrección')
        self.assertEqual(ctx.exception.code, 'insufficient_stock')


class ReverseEdgeCaseTests(LedgerTestCase):
    def test_a_counter_movement_cannot_be_reversed_through_the_facade(self):  # EDGE-03
        entry, _ = self.record('in', '10')
        counter = inventory.reverse_movement(self.company.id, entry.id, user_id=None, user_name='ana', reason='Corrección')
        with self.assertRaises(MovementConflict) as ctx:
            inventory.reverse_movement(self.company.id, counter.id, user_id=None, user_name='ana', reason='Corrección')
        self.assertEqual(ctx.exception.code, 'cannot_reverse_reversal')

    def test_retrying_a_reversed_source_operation_returns_the_reversed_movement(self):  # ADR: política de reintento
        entry, _ = self.record('in', '10', source_type='purchase_receipt', source_id='R-1')
        inventory.reverse_movement(self.company.id, entry.id, user_id=None, user_name='ana', reason='Corrección')
        again, created = self.record('in', '10', source_type='purchase_receipt', source_id='R-1')
        self.assertEqual((again.id, created, again.status), (entry.id, False, 'reversed'))
        self.assertEqual(self.balance(), Decimal('0'))


class PortsTests(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(stock_history.register, None)
        stock_history.register(inventory.has_history)

    def test_history_appears_with_the_first_movement(self):  # INV-09, AC-09
        self.assertFalse(stock_history.has_history(self.company.id, self.product.id))
        self.record()
        self.assertTrue(stock_history.has_history(self.company.id, self.product.id))
        self.assertFalse(stock_history.has_history(make_company('Otra').id, self.product.id))

    def test_warehouse_with_balance_cannot_be_deactivated(self):  # AC-09
        other = make_warehouse(self.company, 'Otra bodega')
        self.record('in', '4', warehouse_id=other.id)
        admin = make_admin(self.company, username='ana')
        set_enabled(self.company, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        from rest_framework.test import APIClient
        client = APIClient()
        authenticate(client, admin)
        response = client.post(f'/api/warehouses/{other.id}/deactivate/')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'warehouse_has_stock'))
        self.record('out', '4', warehouse_id=other.id)
        self.assertEqual(client.post(f'/api/warehouses/{other.id}/deactivate/').status_code, 200)

    def test_product_with_history_cannot_change_tracking(self):  # AC-09
        self.record()
        admin = make_admin(self.company, username='ana')
        set_enabled(self.company, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        from rest_framework.test import APIClient
        client = APIClient()
        authenticate(client, admin)
        response = client.patch(f'/api/products/{self.product.id}/', {'tracks_stock': False}, format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'stock_history_locked'))


class ConcurrencyTests(TransactionTestCase):
    def run_threads(self, work, count=2):
        barrier = Barrier(count)
        errors: list[Exception] = []

        def target():
            try:
                barrier.wait()
                work()
            except Exception as exc:  # noqa: BLE001 - se verifica en la prueba
                errors.append(exc)
            finally:
                connection.close()

        threads = [Thread(target=target) for _ in range(count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return errors

    def test_simultaneous_confirmations_of_the_same_document_create_one_movement(self):  # EDGE-01, AC-03
        company = make_company('Empresa C')
        product, warehouse = make_product(company), make_warehouse(company)

        def work():
            inventory.record_movement(
                company.id, product_id=product.id, warehouse_id=warehouse.id, kind='in', quantity=Decimal('5'),
                user_id=None, user_name='ana', source_type='sales_order', source_id='99')

        self.assertEqual(self.run_threads(work, count=3), [])
        self.assertEqual(StockMovementModel.objects.filter(company_id=company.id).count(), 1)

    def test_simultaneous_exits_cannot_overdraw_the_balance(self):  # EDGE-04
        company = make_company('Empresa D')
        product, warehouse = make_product(company), make_warehouse(company)
        inventory.record_movement(
            company.id, product_id=product.id, warehouse_id=warehouse.id, kind='in', quantity=Decimal('5'),
            user_id=None, user_name='ana')
        counter = iter(range(100))

        def work():
            inventory.record_movement(
                company.id, product_id=product.id, warehouse_id=warehouse.id, kind='out', quantity=Decimal('5'),
                user_id=None, user_name='ana', source_type='sales_order', source_id=f'o{next(counter)}')

        errors = self.run_threads(work, count=2)
        self.assertEqual([getattr(e, 'code', None) for e in errors], ['insufficient_stock'])
        self.assertEqual(inventory.get_balance(company.id, product.id, warehouse.id), Decimal('0'))


    def test_simultaneous_reversals_create_a_single_counter_movement(self):  # EDGE-03
        company = make_company('Empresa E')
        product, warehouse = make_product(company), make_warehouse(company)
        entry, _ = inventory.record_movement(
            company.id, product_id=product.id, warehouse_id=warehouse.id, kind='in', quantity=Decimal('5'),
            user_id=None, user_name='ana')

        def work():
            inventory.reverse_movement(company.id, entry.id, user_id=None, user_name='ana', reason='Corrección')

        errors = self.run_threads(work, count=2)
        self.assertEqual([getattr(e, 'code', None) for e in errors], ['already_reversed'])
        self.assertEqual(StockMovementModel.objects.filter(company_id=company.id, reverses_id=entry.id).count(), 1)
        self.assertEqual(inventory.get_balance(company.id, product.id, warehouse.id), Decimal('0'))


class MovementApiTests(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.admin = make_admin(self.company, username='ana')
        authenticate(self.client, self.admin)
        set_enabled(self.company, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        self.product = make_product(self.company)
        self.warehouse = make_warehouse(self.company)

    def record(self, kind='in', quantity='10', **extra):
        values = dict(product_id=self.product.id, warehouse_id=self.warehouse.id, kind=kind,
                      quantity=Decimal(quantity), user_id=self.admin.id, user_name='ana', occurred_at=WHEN)
        values.update(extra)
        return inventory.record_movement(self.company.id, **values)[0]

    def test_list_shows_in_and_out_in_separate_columns(self):  # AC-04
        self.record('in', '10', reference='Compra 1')
        self.record('out', '2.5', reference='PV-1', source_type='sales_order', source_id='42')
        results = self.client.get(URL).json()['results']
        self.assertEqual(len(results), 2)
        by_kind = {r['kind']: r for r in results}
        self.assertEqual((by_kind['in']['quantity_in'], by_kind['in']['quantity_out']), ('10.0000', None))
        self.assertEqual((by_kind['out']['quantity_in'], by_kind['out']['quantity_out']), (None, '2.5000'))
        row = by_kind['out']
        self.assertEqual((row['product']['name'], row['warehouse']['name'], row['unit']['abbreviation']),
                         ('Arroz', 'Central', 'kg'))
        self.assertEqual(row['source'], {'type': 'sales_order', 'label': 'Pedido de venta', 'id': '42',
                                         'line': '', 'reference': 'PV-1', 'available': True})
        self.assertIsNone(by_kind['in']['source'])

    def test_retried_confirmation_shows_a_single_row(self):  # AC-03 / aceptación de interfaz
        for _ in range(3):
            self.record(source_type='sales_order', source_id='42')
        self.assertEqual(self.client.get(URL).json()['count'], 1)

    def test_filters(self):  # AC-05
        other_product = make_product(self.company, 'Frijol', abbreviation='lb')
        other_warehouse = make_warehouse(self.company, 'Bodega')
        self.record('in', '10', occurred_at=datetime(2026, 10, 1, 12, tzinfo=dt_timezone.utc))
        self.record('out', '1', source_type='sales_order', source_id='1')
        self.record('in', '3', product_id=other_product.id, warehouse_id=other_warehouse.id,
                    source_type='purchase_receipt', source_id='9')

        def count(**params):
            response = self.client.get(URL, params)
            self.assertEqual(response.status_code, 200, response.content)
            return response.json()['count']

        self.assertEqual(count(), 3)
        self.assertEqual(count(date_from='2026-10-10'), 2)
        self.assertEqual(count(date_to='2026-10-10'), 1)
        self.assertEqual(count(product_id=str(other_product.id)), 1)
        self.assertEqual(count(warehouse_id=str(other_warehouse.id)), 1)
        self.assertEqual(count(kind='in'), 2)
        self.assertEqual(count(source_type='sales_order'), 1)
        self.assertEqual(count(source_type='none'), 1)

    @override_settings(TIME_ZONE='America/La_Paz')
    def test_date_filters_use_the_local_day_at_the_boundary(self):  # AC-05
        # 2026-10-21 02:00 UTC = 2026-10-20 22:00 en La Paz (UTC-4): pertenece al día 20.
        self.record(occurred_at=datetime(2026, 10, 21, 2, 0, tzinfo=dt_timezone.utc))

        def count(**params):
            return self.client.get(URL, params).json()['count']

        self.assertEqual(count(date_from='2026-10-20', date_to='2026-10-20'), 1)
        self.assertEqual(count(date_from='2026-10-21'), 0)
        self.assertEqual(count(date_to='2026-10-19'), 0)

    def test_invalid_filters_are_400_per_parameter(self):  # EDGE-05
        response = self.client.get(URL, {'date_from': 'ayer', 'product_id': 'x', 'kind': 'z', 'source_type': 'q'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'date_from', 'product_id', 'kind', 'source_type'})
        response = self.client.get(URL, {'date_from': '2026-10-10', 'date_to': '2026-10-01'})
        self.assertIn('date_to', response.json())

    def test_detail_reconstructs_the_operation_and_counter_movement(self):  # AC-06
        entry = self.record('in', '10', reference='Compra 1', reason='Recepción', source_type='purchase_receipt',
                            source_id='R-1')
        counter = inventory.reverse_movement(self.company.id, entry.id, user_id=self.admin.id, user_name='ana', reason='Corrección')
        detail = self.client.get(f'{URL}{entry.id}/').json()
        self.assertEqual(detail['status'], 'reversed')
        self.assertEqual(detail['reversed_by']['id'], str(counter.id))
        self.assertEqual((detail['user']['name'], detail['reason'], detail['quantity']), ('ana', 'Recepción', '10.0000'))
        counter_detail = self.client.get(f'{URL}{counter.id}/').json()
        self.assertEqual((counter_detail['status'], counter_detail['kind'], counter_detail['reverses']),
                         ('confirmed', 'out', {'id': str(entry.id)}))

    def test_source_is_unavailable_when_its_module_is_disabled(self):  # AC-07
        self.record(source_type='purchase_receipt', source_id='R-1')
        self.record('out', '1', source_type='sales_order', source_id='1')
        rows = {r['source']['type']: r['source']['available'] for r in self.client.get(URL).json()['results']}
        self.assertEqual(rows, {'purchase_receipt': False, 'sales_order': True})

    def test_read_only(self):  # AC-02
        movement = self.record()
        for method in ('post', 'put', 'patch', 'delete'):
            self.assertEqual(getattr(self.client, method)(URL).status_code, 405, method)
            self.assertEqual(getattr(self.client, method)(f'{URL}{movement.id}/').status_code, 405, method)

    def test_isolated_between_companies_and_404(self):  # INV-08
        movement = self.record()
        other = make_company('Empresa B')
        authenticate(self.client, make_admin(other, username='bea'))
        set_enabled(other, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        self.assertEqual(self.client.get(URL).json()['count'], 0)
        self.assertEqual(self.client.get(f'{URL}{movement.id}/').status_code, 404)

    def test_requires_inventory_module_and_authentication(self):
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.client.credentials()
        self.assertIn(self.client.get(URL).status_code, (401, 403))
