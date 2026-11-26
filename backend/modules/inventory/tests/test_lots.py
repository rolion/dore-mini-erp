"""TASK-lotes-disponibilidad-inventario: lotes, físico vs. disponible para empaque (AC-01..AC-15)."""
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from uuid import UUID, uuid4

from django.test import SimpleTestCase

from modules.accounting.infrastructure.django.models import FiscalPeriodModel
from modules.inventory import services as inventory
from modules.inventory.domain.exceptions import (
    InsufficientStock,
    LotNotFound,
    LotNumberingRejected,
    MovementConflict,
    MovementValidationError,
)
from modules.inventory.domain.lot import LotNumber, LotStatus, StockLot, format_lot_code
from modules.inventory.infrastructure.django.models import LotNumberCounterModel, StockLotModel, StockMovementModel
from modules.sales.tests.periods import open_test_period

from .policy import set_negative_stock
from .test_stock import StockApiTestCase

LOTS = '/api/stock-lots/'
WHEN = datetime(2026, 11, 26, 15, 0, tzinfo=dt_timezone.utc)


class LotDomainTests(SimpleTestCase):
    def lot(self):
        return StockLot.create(product_id=uuid4(), warehouse_id=uuid4(), lot_date=date(2026, 11, 26),
                               number=LotNumber(uuid4(), 'Gestión 2026', 1))

    def test_code_is_date_plus_period_number_padded_to_four_digits(self):  # INV-07
        self.assertEqual(format_lot_code(date(2026, 11, 26), 1), 'L-20261126-0001')
        self.assertEqual(format_lot_code(date(2026, 1, 5), 12345), 'L-20260105-12345')
        self.assertEqual(self.lot().code, 'L-20261126-0001')

    def test_lot_is_born_refrigerating_and_blocks_its_stock(self):  # AC-05
        lot = self.lot()
        self.assertIs(lot.status, LotStatus.REFRIGERATING)
        self.assertEqual(lot.available(Decimal('118')), Decimal('0'))

    def test_release_is_one_way_and_idempotent(self):  # AC-06, INV-06
        lot = self.lot()
        self.assertTrue(lot.release(now=WHEN, user_id=None, user_name='ana'))
        self.assertEqual(lot.available(Decimal('118')), Decimal('118'))
        self.assertFalse(lot.release(now=datetime(2026, 12, 1, tzinfo=dt_timezone.utc), user_id=None, user_name='beto'))
        self.assertEqual((lot.released_at, lot.released_by_name), (WHEN, 'ana'))


class LotTestCase(StockApiTestCase):
    def setUp(self):
        super().setUp()
        self.period = open_test_period(self.company.id)
        self.product = UUID(self.make_product('Cuñapé granel'))
        self.wh = UUID(self.warehouse)
        self.n = 0

    def make_lot(self, quantity='118', source_id=None, **extra):
        self.n += 1
        return inventory.create_lot(
            self.company.id, product_id=self.product, warehouse_id=self.wh, quantity=Decimal(quantity),
            source_type='production_order', source_id=source_id or f'OP-{self.n}', user_id=None, user_name='ana',
            occurred_at=extra.get('occurred_at', WHEN))

    def move(self, kind, quantity, lot_id=None, source_id=None):
        return inventory.record_movement(
            self.company.id, product_id=self.product, warehouse_id=self.wh, kind=kind, quantity=Decimal(quantity),
            user_id=None, user_name='ana', lot_id=lot_id,
            **({'source_type': 'sales_order', 'source_id': source_id} if source_id else {}))

    def physical(self):
        return inventory.get_balance(self.company.id, self.product, self.wh)


class CreateAndReleaseLotTests(LotTestCase):
    def test_create_lot_enters_refrigerating_with_physical_and_no_available(self):  # AC-01, AC-05
        lot, movement, created = self.make_lot('118')
        self.assertTrue(created)
        self.assertEqual(lot.code, 'L-20261126-0001')
        self.assertEqual((lot.status, lot.physical_quantity, lot.available_quantity),
                         ('refrigerating', Decimal('118'), Decimal('0')))
        self.assertEqual((movement.kind, movement.lot_id), ('in', lot.id))
        self.assertEqual(self.physical(), Decimal('118'))

    def test_create_lot_is_idempotent_by_source_and_spends_no_number(self):  # AC-02
        first, movement, _ = self.make_lot('118', source_id='OP-1')
        again, same_movement, created = self.make_lot('118', source_id='OP-1')
        self.assertFalse(created)
        self.assertEqual((again.id, same_movement.id), (first.id, movement.id))
        self.assertEqual(StockMovementModel.objects.filter(lot_id=first.id).count(), 1)
        self.assertEqual(self.make_lot('5')[0].code, 'L-20261126-0002')

    def test_retry_with_another_quantity_conflicts(self):  # AC-02
        self.make_lot('118', source_id='OP-1')
        with self.assertRaises(MovementConflict) as raised:
            self.make_lot('100', source_id='OP-1')
        self.assertEqual(raised.exception.code, 'source_operation_mismatch')

    def test_number_is_per_fiscal_period_and_restarts_in_the_next_one(self):  # AC-03
        FiscalPeriodModel.objects.create(
            company_id=self.company.id, name='Gestión 2027', start_date=date(2027, 1, 1), end_date=date(2027, 12, 31),
            status='OPEN')
        codes = [self.make_lot('1')[0].code, self.make_lot('1')[0].code]
        later = self.make_lot('1', occurred_at=datetime(2027, 1, 2, 12, 0, tzinfo=dt_timezone.utc))[0].code
        self.assertEqual(codes, ['L-20261126-0001', 'L-20261126-0002'])
        self.assertEqual(later, 'L-20270102-0001')

    def test_without_an_open_period_nothing_is_created(self):  # AC-04
        FiscalPeriodModel.objects.filter(company_id=self.company.id).delete()
        with self.assertRaises(LotNumberingRejected) as raised:
            self.make_lot('118')
        self.assertEqual(raised.exception.code, 'fiscal_period_missing')
        self.assertEqual(StockLotModel.objects.count(), 0)

    def test_closed_period_blocks_creation(self):  # AC-04
        FiscalPeriodModel.objects.filter(company_id=self.company.id).update(status='CLOSED')
        with self.assertRaises(LotNumberingRejected) as raised:
            self.make_lot('118')
        self.assertEqual(raised.exception.code, 'fiscal_period_closed')
        self.assertEqual(StockLotModel.objects.count(), 0)

    def test_an_invalid_entry_rolls_back_lot_and_number(self):  # AC-01, INV-07
        with self.assertRaises(MovementValidationError):
            self.make_lot('1.5')  # unidad entera: no admite fracciones
        # Nada queda: ni el lote ni el número consumido (el contador se creó dentro de la misma transacción).
        self.assertEqual((StockLotModel.objects.count(), LotNumberCounterModel.objects.count()), (0, 0))
        self.assertEqual(self.make_lot('2')[0].code, 'L-20261126-0001')

    def test_release_makes_the_physical_stock_available_and_is_idempotent(self):  # AC-06
        lot = self.make_lot('118')[0]
        released, changed = inventory.release_lot(self.company.id, lot.id, user_id=None, user_name='ana')
        self.assertTrue(changed)
        self.assertEqual((released.status, released.physical_quantity, released.available_quantity),
                         ('released', Decimal('118'), Decimal('118')))
        self.assertEqual(released.released_by_name, 'ana')
        again, changed_again = inventory.release_lot(self.company.id, lot.id, user_id=None, user_name='beto')
        self.assertFalse(changed_again)
        self.assertEqual((again.released_at, again.released_by_name), (released.released_at, 'ana'))
        self.assertEqual(StockMovementModel.objects.count(), 1)

    def test_release_of_unknown_lot_fails(self):
        with self.assertRaises(LotNotFound):
            inventory.release_lot(self.company.id, uuid4(), user_id=None, user_name='ana')


class LotOutputRulesTests(LotTestCase):
    def test_refrigerating_lot_cannot_be_consumed(self):  # AC-07, INV-02
        lot = self.make_lot('118')[0]
        with self.assertRaises(MovementConflict) as raised:
            self.move('out', '6', lot_id=lot.id)
        self.assertEqual(raised.exception.code, 'lot_not_released')
        self.assertEqual(self.physical(), Decimal('118'))

    def test_released_lot_supplies_packing_up_to_its_balance(self):  # AC-07
        lot = self.make_lot('120')[0]
        inventory.release_lot(self.company.id, lot.id, user_id=None, user_name='ana')
        self.move('out', '80', lot_id=lot.id)
        self.move('out', '36', lot_id=lot.id)
        self.assertEqual(inventory.get_lot(self.company.id, lot.id).available_quantity, Decimal('4'))
        with self.assertRaises(InsufficientStock) as raised:
            self.move('out', '5', lot_id=lot.id)
        self.assertEqual(raised.exception.available, Decimal('4'))

    def test_a_lot_never_goes_negative_even_with_negative_stock_allowed(self):  # INV-01
        set_negative_stock(self.company, True)
        lot = self.make_lot('10')[0]
        inventory.release_lot(self.company.id, lot.id, user_id=None, user_name='ana')
        with self.assertRaises(InsufficientStock):
            self.move('out', '11', lot_id=lot.id)

    def test_lot_of_another_product_or_warehouse_is_rejected(self):  # INV-09
        lot = self.make_lot('10')[0]
        inventory.release_lot(self.company.id, lot.id, user_id=None, user_name='ana')
        other = UUID(self.make_product('Otro'))
        with self.assertRaises(MovementValidationError):
            inventory.record_movement(
                self.company.id, product_id=other, warehouse_id=self.wh, kind='out', quantity=Decimal('1'),
                user_id=None, user_name='ana', lot_id=lot.id)

    def test_stock_cannot_be_added_to_an_existing_lot(self):  # INV-04
        lot = self.make_lot('10')[0]
        with self.assertRaises(MovementValidationError):
            self.move('in', '5', lot_id=lot.id)

    def test_output_without_lot_only_consumes_unlotted_stock(self):  # AC-08, INV-03 (ejemplo 118/60/22)
        self.move('in', '22')
        refrigerating = self.make_lot('118')[0]
        released = self.make_lot('60')[0]
        inventory.release_lot(self.company.id, released.id, user_id=None, user_name='ana')
        with self.assertRaises(InsufficientStock) as raised:
            self.move('out', '30', source_id='V-1')
        self.assertEqual(raised.exception.available, Decimal('22'))
        self.move('out', '22', source_id='V-2')
        self.assertEqual(self.physical(), Decimal('178'))
        self.assertEqual(inventory.get_lot(self.company.id, refrigerating.id).physical_quantity, Decimal('118'))
        self.assertEqual(inventory.get_lot(self.company.id, released.id).physical_quantity, Decimal('60'))

    def test_document_outputs_use_the_same_rule(self):  # AC-09
        self.move('in', '22')
        self.make_lot('118')
        with self.assertRaises(InsufficientStock):
            inventory.record_outputs(
                self.company.id, warehouse_id=self.wh, lines=[(self.product, Decimal('30'))],
                source_type='sales_order', source_id='V-9', user_id=None, user_name='ana')
        inventory.record_outputs(
            self.company.id, warehouse_id=self.wh, lines=[(self.product, Decimal('22'))],
            source_type='sales_order', source_id='V-9', user_id=None, user_name='ana')

    def test_negative_policy_lets_unlotted_go_negative_but_never_touches_lots(self):  # INV-03
        set_negative_stock(self.company, True)
        lot = self.make_lot('118')[0]
        self.move('out', '5', source_id='V-1')
        self.assertEqual(inventory.get_lot(self.company.id, lot.id).physical_quantity, Decimal('118'))
        self.assertEqual(self.physical(), Decimal('113'))

    def test_adjustment_out_is_limited_to_unlotted_stock(self):  # AC-09
        self.move('in', '4')
        self.make_lot('118')
        body = {'adjustment_id': str(uuid4()), 'product_id': str(self.product), 'warehouse_id': self.warehouse,
                'counted_quantity': '100', 'reason': 'Conteo', 'expected_system_quantity': '122'}
        response = self.client.post('/api/stock-adjustments/', body, format='json')
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(self.physical(), Decimal('122'))

    def test_products_without_lots_behave_as_before(self):  # AC-12, INV-06
        self.move('in', '10')
        with self.assertRaises(InsufficientStock):
            self.move('out', '11', source_id='V-1')
        self.move('out', '10', source_id='V-2')
        self.assertEqual(self.physical(), Decimal('0'))


class LotReversalTests(LotTestCase):
    def test_reversing_a_lot_output_returns_the_units_to_that_lot(self):  # AC-10
        lot = self.make_lot('50')[0]
        inventory.release_lot(self.company.id, lot.id, user_id=None, user_name='ana')
        out = self.move('out', '20', lot_id=lot.id)[0]
        counter = inventory.reverse_movement(self.company.id, out.id, user_id=None, user_name='ana', reason='Error')
        self.assertEqual(counter.lot_id, lot.id)
        self.assertEqual(inventory.get_lot(self.company.id, lot.id).physical_quantity, Decimal('50'))

    def test_reversing_the_lot_entry_requires_the_lot_balance(self):  # AC-10, INV-05
        lot, entry, _ = self.make_lot('50')
        inventory.release_lot(self.company.id, lot.id, user_id=None, user_name='ana')
        self.move('out', '20', lot_id=lot.id)
        with self.assertRaises(InsufficientStock) as raised:
            inventory.reverse_movement(self.company.id, entry.id, user_id=None, user_name='ana', reason='Error')
        self.assertEqual(raised.exception.available, Decimal('30'))

    def test_reversing_an_untouched_refrigerating_lot_entry_works_even_with_negative_policy(self):  # INV-05
        set_negative_stock(self.company, True)
        lot, entry, _ = self.make_lot('50')
        inventory.reverse_movement(self.company.id, entry.id, user_id=None, user_name='ana', reason='Error')
        self.assertEqual(inventory.get_lot(self.company.id, lot.id).physical_quantity, Decimal('0'))

    def test_reversing_the_source_of_a_lot_checks_the_lot_not_the_total(self):  # AC-10
        lot = self.make_lot('50', source_id='OP-7')[0]
        inventory.release_lot(self.company.id, lot.id, user_id=None, user_name='ana')
        self.move('in', '100')  # stock sin lote: el total alcanzaría, el lote no
        self.move('out', '20', lot_id=lot.id)
        with self.assertRaises(InsufficientStock):
            inventory.reverse_source_movements(
                self.company.id, 'production_order', 'OP-7', user_id=None, user_name='ana', reason='Error')
        self.assertEqual(self.physical(), Decimal('130'))


class LotApiTests(LotTestCase):
    def rows(self, **params):
        response = self.client.get(LOTS, params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['results']

    def test_list_shows_product_warehouse_lot_physical_available_and_status(self):  # AC-11, AC-05
        lot = self.make_lot('118')[0]
        row = self.rows()[0]
        self.assertEqual(
            (row['id'], row['code'], row['status'], row['product_name'], row['warehouse_name'],
             row['physical_quantity'], row['available_quantity']),
            (str(lot.id), 'L-20261126-0001', 'refrigerating', 'Cuñapé granel', 'Almacén principal',
             '118.0000', '0.0000'))
        self.assertEqual(row['unit'], {'abbreviation': 'u', 'allows_fractions': False})

    def test_list_filters(self):  # AC-11
        first = self.make_lot('10')[0]
        second = self.make_lot('20')[0]
        inventory.release_lot(self.company.id, second.id, user_id=None, user_name='ana')
        self.move('out', '20', lot_id=second.id)
        self.assertEqual({r['id'] for r in self.rows()}, {str(first.id), str(second.id)})
        self.assertEqual([r['id'] for r in self.rows(status='released')], [str(second.id)])
        self.assertEqual([r['id'] for r in self.rows(with_stock='true')], [str(first.id)])
        self.assertEqual([r['id'] for r in self.rows(search='0002')], [str(second.id)])
        self.assertEqual(len(self.rows(product_id=str(self.product), warehouse_id=self.warehouse)), 2)
        self.assertEqual(self.rows(product_id=str(uuid4())), [])
        self.assertEqual(self.client.get(LOTS, {'status': 'x'}).status_code, 400)
        self.assertEqual(self.client.get(LOTS, {'warehouse_id': 'no'}).status_code, 400)

    def test_detail_and_other_company_isolation(self):  # AC-11
        from modules.accounts.testing import authenticate, make_admin, make_company
        from rest_framework.test import APIClient

        from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
        from modules.modularity.tests.test_enforcement import set_enabled
        lot = self.make_lot('118')[0]
        self.assertEqual(self.client.get(f'{LOTS}{lot.id}/').json()['code'], lot.code)
        self.assertEqual(self.client.get(f'{LOTS}{uuid4()}/').status_code, 404)
        other = make_company('Empresa B')
        client = APIClient()
        authenticate(client, make_admin(other, username='beto'))
        set_enabled(other, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        self.assertEqual(client.get(LOTS).json()['count'], 0)
        self.assertEqual(client.get(f'{LOTS}{lot.id}/').status_code, 404)

    def test_lots_require_the_inventory_module(self):  # Authorization
        from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
        from modules.modularity.tests.test_enforcement import set_enabled
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)
        self.assertEqual(self.client.get(LOTS).status_code, 403)

    def test_stock_exposes_has_lots_and_keeps_the_physical_quantity(self):  # AC-13, AC-12
        plain = self.make_product('Sin lotes')
        self.make_lot('118')
        rows = {r['product_id']: r for r in self.client.get('/api/stock/').json()['results']}
        self.assertTrue(rows[str(self.product)]['has_lots'])
        self.assertEqual(rows[str(self.product)]['quantity'], '118.0000')
        self.assertFalse(rows[plain]['has_lots'])
        detail = self.client.get(f'/api/stock/{self.product}/{self.warehouse}/').json()
        self.assertTrue(detail['has_lots'])

    def test_movement_exposes_its_lot(self):  # AC-13
        lot, entry, _ = self.make_lot('118')
        plain = self.move('in', '3')[0]
        self.assertEqual(self.client.get(f'/api/stock-movements/{entry.id}/').json()['lot'],
                         {'id': str(lot.id), 'code': lot.code})
        self.assertIsNone(self.client.get(f'/api/stock-movements/{plain.id}/').json()['lot'])
        listed = {r['id']: r['lot'] for r in self.client.get('/api/stock-movements/').json()['results']}
        self.assertEqual(listed[str(entry.id)]['code'], lot.code)
