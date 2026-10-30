"""PB-INV-008: revertir movimientos mediante contramovimientos."""
from decimal import Decimal
from threading import Barrier, Thread

from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.inventory import services as inventory
from modules.inventory.domain.exceptions import InsufficientStock, MovementValidationError
from modules.inventory.domain.movement import MovementKind, StockMovement, reversal_block
from modules.inventory.infrastructure.django.models import StockMovementModel
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled

from .policy import set_negative_stock
from .test_movements import WHEN, make_product, make_warehouse

URL = '/api/stock-movements/'


class ReversalDomainTests(SimpleTestCase):
    def movement(self):
        from uuid import uuid4
        return StockMovement.record(
            product_id=uuid4(), warehouse_id=uuid4(), kind=MovementKind.IN, quantity='5', occurred_at=WHEN,
            user_id=None, user_name='ana')

    def test_reason_is_required_and_limited(self):  # INV-02, AC-01
        for bad in ('', '   ', None, 'x' * 201):
            movement = self.movement()
            with self.assertRaises(MovementValidationError, msg=repr(bad)) as ctx:
                movement.reverse(occurred_at=WHEN, user_id=None, user_name='ana', reason=bad)
            self.assertIn('reason', ctx.exception.errors)
            self.assertEqual(movement.status.value, 'confirmed')

    def test_reversal_block_by_origin_and_state(self):  # INV-03, AC-12
        from modules.inventory.domain.movement import MovementSource
        movement = self.movement()
        self.assertIsNone(reversal_block(movement))
        movement.source = MovementSource('sales_order', '1')
        self.assertEqual(reversal_block(movement)[0], 'requires_return')
        movement.source = MovementSource('purchase_receipt', '1')
        self.assertEqual(reversal_block(movement)[0], 'reverse_from_origin')
        movement.source = MovementSource('inventory_adjustment', '1')
        self.assertIsNone(reversal_block(movement))
        counter = movement.reverse(occurred_at=WHEN, user_id=None, user_name='ana', reason='Error')
        self.assertEqual(reversal_block(movement)[0], 'already_reversed')
        self.assertEqual(reversal_block(counter)[0], 'cannot_reverse_reversal')


class ReversalApiTests(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa R')
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

    def reverse(self, movement, **body):
        return self.client.post(f'{URL}{movement.id}/reverse/', body, format='json')

    def balance(self):
        return inventory.get_balance(self.company.id, self.product.id, self.warehouse.id)

    def test_reason_is_required(self):  # AC-01
        entry = self.record()
        for body in ({}, {'reason': ''}, {'reason': '   '}, {'reason': 'x' * 201}):
            response = self.reverse(entry, **body)
            self.assertEqual(response.status_code, 400, body)
            self.assertIn('reason', response.json())
        self.assertEqual(StockMovementModel.objects.get(pk=entry.id).status, 'confirmed')

    def test_manual_movement_is_reversed_with_a_linked_counter_movement(self):  # AC-02, AC-11
        entry = self.record('in', '10', reference='Carga')
        response = self.reverse(entry, reason='  Error de carga ')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['kind'], body['quantity'], body['reason'], body['reverses']['id']),
                         ('out', '10.0000', 'Error de carga', str(entry.id)))
        self.assertEqual(body['user']['name'], 'ana')
        self.assertEqual(self.balance(), Decimal('0'))
        original = self.client.get(f'{URL}{entry.id}/').json()
        self.assertEqual(original['status'], 'reversed')
        self.assertEqual(original['reversed_by']['id'], body['id'])
        self.assertEqual((original['reversed_by']['reason'], original['reversed_by']['user']['name']),
                         ('Error de carga', 'ana'))
        self.assertTrue(original['reversed_by']['reference'] is not None and original['reversed_by']['occurred_at'])
        self.assertEqual(original['reversal'], {
            'allowed': False, 'code': 'already_reversed', 'message': 'El movimiento ya fue revertido.'})
        self.assertEqual(StockMovementModel.objects.filter(company_id=self.company.id).count(), 2)

    def test_adjustment_and_opening_origins_are_reversible(self):  # AC-02, EDGE-04, EDGE-05
        for index, source in enumerate(('inventory_adjustment', 'inventory_opening')):
            entry = self.record('in', '1', source_type=source, source_id=f'x{index}')
            self.assertTrue(self.client.get(f'{URL}{entry.id}/').json()['reversal']['allowed'])
            self.assertEqual(self.reverse(entry, reason='Corrección').status_code, 200)

    def test_second_reversal_and_reversing_a_counter_are_409(self):  # AC-03
        entry = self.record()
        counter = self.reverse(entry, reason='Uno').json()
        again = self.reverse(entry, reason='Dos')
        self.assertEqual((again.status_code, again.json()['code']), (409, 'already_reversed'))
        on_counter = self.client.post(f'{URL}{counter["id"]}/reverse/', {'reason': 'Tres'}, format='json')
        self.assertEqual((on_counter.status_code, on_counter.json()['code']), (409, 'cannot_reverse_reversal'))
        self.assertEqual(StockMovementModel.objects.filter(company_id=self.company.id).count(), 2)

    def test_sales_and_purchase_origins_are_rejected(self):  # AC-04, AC-12
        self.record('in', '5')
        sale = self.record('out', '2', source_type='sales_order', source_id='42')
        receipt = self.record('in', '3', source_type='purchase_receipt', source_id='R-1')
        for movement, code in ((sale, 'requires_return'), (receipt, 'reverse_from_origin')):
            detail = self.client.get(f'{URL}{movement.id}/').json()['reversal']
            self.assertEqual((detail['allowed'], detail['code']), (False, code))
            self.assertTrue(detail['message'])
            response = self.reverse(movement, reason='Corrección')
            self.assertEqual((response.status_code, response.json()['code']), (409, code))
            self.assertEqual(StockMovementModel.objects.get(pk=movement.id).status, 'confirmed')
        self.assertEqual(StockMovementModel.objects.filter(company_id=self.company.id).count(), 3)

    def test_blocked_by_stock_policy_shows_product_and_balance(self):  # AC-05
        entry = self.record('in', '10')
        self.record('out', '8')
        response = self.reverse(entry, reason='Corrección')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'insufficient_stock'))
        body = response.json()
        self.assertEqual((body['product']['name'], body['available'], body['requested']), ('Arroz', '2.000', '10.000'))
        self.assertEqual(StockMovementModel.objects.get(pk=entry.id).status, 'confirmed')
        set_negative_stock(self.company, True)
        self.assertEqual(self.reverse(entry, reason='Corrección').status_code, 200)
        self.assertEqual(self.balance(), Decimal('-8'))

    def test_other_company_movement_is_404(self):  # AC-13
        other = make_company('Empresa X')
        product, warehouse = make_product(other), make_warehouse(other)
        foreign, _ = inventory.record_movement(
            other.id, product_id=product.id, warehouse_id=warehouse.id, kind='in', quantity=Decimal('1'),
            user_id=None, user_name='bea')
        self.assertEqual(self.reverse(foreign, reason='Corrección').status_code, 404)
        self.assertEqual(self.client.post(f'{URL}{self.product.id}/reverse/', {'reason': 'x'}).status_code, 404)

    def test_module_disabled_blocks_the_endpoint(self):  # AC-14
        entry = self.record()
        set_enabled(self.company, list(DEFAULT_ENABLED_KEYS))
        self.assertEqual(self.reverse(entry, reason='Corrección').status_code, 403)

    def test_get_is_the_only_other_method(self):  # contrato
        entry = self.record()
        self.assertEqual(self.client.get(f'{URL}{entry.id}/reverse/').status_code, 405)


class ReverseSourceMovementsTests(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa S')
        self.warehouse = make_warehouse(self.company)
        self.rice = make_product(self.company, 'Arroz')
        self.beans = make_product(self.company, 'Frijol', abbreviation='lb')

    def enter(self, product, quantity, source_id='R-1'):
        inventory.record_movement(
            self.company.id, product_id=product.id, warehouse_id=self.warehouse.id, kind='in',
            quantity=Decimal(quantity), user_id=None, user_name='ana', source_type='purchase_receipt',
            source_id=source_id, source_line=str(product.id))

    def balance(self, product):
        return inventory.get_balance(self.company.id, product.id, self.warehouse.id)

    def reverse(self, source_id='R-1'):
        return inventory.reverse_source_movements(
            self.company.id, 'purchase_receipt', source_id, user_id=None, user_name='ana', reason='Error')

    def test_all_movements_of_the_document_are_reversed(self):  # AC-06
        self.enter(self.rice, '10')
        self.enter(self.beans, '4')
        counters = self.reverse()
        self.assertEqual({(c.kind, c.quantity) for c in counters}, {('out', Decimal('10')), ('out', Decimal('4'))})
        self.assertEqual((self.balance(self.rice), self.balance(self.beans)), (Decimal('0'), Decimal('0')))
        self.assertEqual(StockMovementModel.objects.filter(status='reversed').count(), 2)
        moves = inventory.list_movements_for_source(self.company.id, 'purchase_receipt', 'R-1')
        self.assertTrue(all(m.status == 'reversed' and m.reversed_by_id for m in moves))

    def test_repeating_returns_nothing_and_changes_nothing(self):  # AC-09
        self.enter(self.rice, '10')
        self.reverse()
        self.assertEqual(self.reverse(), [])
        self.assertEqual(StockMovementModel.objects.count(), 2)

    def test_all_or_nothing_with_every_shortage_reported(self):  # AC-07, INV-05
        self.enter(self.rice, '10')
        self.enter(self.beans, '4')
        inventory.record_movement(
            self.company.id, product_id=self.rice.id, warehouse_id=self.warehouse.id, kind='out',
            quantity=Decimal('8'), user_id=None, user_name='ana')
        inventory.record_movement(
            self.company.id, product_id=self.beans.id, warehouse_id=self.warehouse.id, kind='out',
            quantity=Decimal('3'), user_id=None, user_name='ana')
        with self.assertRaises(InsufficientStock) as ctx:
            self.reverse()
        self.assertEqual({s.product_id for s in ctx.exception.shortages}, {self.rice.id, self.beans.id})
        self.assertEqual(StockMovementModel.objects.filter(status='reversed').count(), 0)
        self.assertEqual(StockMovementModel.objects.count(), 4)

    def test_negative_policy_allows_the_reversal(self):  # INV-04
        self.enter(self.rice, '10')
        inventory.record_movement(
            self.company.id, product_id=self.rice.id, warehouse_id=self.warehouse.id, kind='out',
            quantity=Decimal('8'), user_id=None, user_name='ana')
        set_negative_stock(self.company, True)
        self.reverse()
        self.assertEqual(self.balance(self.rice), Decimal('-8'))

    def test_other_company_documents_are_not_touched(self):  # AC-13
        self.enter(self.rice, '10')
        other = make_company('Empresa Z')
        self.assertEqual(inventory.reverse_source_movements(
            other.id, 'purchase_receipt', 'R-1', user_id=None, user_name='bea', reason='x'), [])
        self.assertEqual(StockMovementModel.objects.filter(status='reversed').count(), 0)


class ReverseSourceConcurrencyTests(TransactionTestCase):
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

    def test_simultaneous_document_reversals_create_one_set_of_counters(self):  # AC-03, AC-09
        company = make_company('Empresa K')
        product, warehouse = make_product(company), make_warehouse(company)
        inventory.record_movement(
            company.id, product_id=product.id, warehouse_id=warehouse.id, kind='in', quantity=Decimal('5'),
            user_id=None, user_name='ana', source_type='purchase_receipt', source_id='R-9',
            source_line=str(product.id))

        def work():
            inventory.reverse_source_movements(
                company.id, 'purchase_receipt', 'R-9', user_id=None, user_name='ana', reason='Error')

        self.assertEqual(self.run_threads(work, count=2), [])
        self.assertEqual(StockMovementModel.objects.filter(company_id=company.id, reverses_id__isnull=False).count(), 1)
        self.assertEqual(inventory.get_balance(company.id, product.id, warehouse.id), Decimal('0'))
