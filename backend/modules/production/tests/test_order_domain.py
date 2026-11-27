from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from modules.production.domain.production_order import (
    OrderIngredient, OrderStateError, OrderStatus, OrderValidationError, ProductionOrder, parse_preparations,
    parse_quantity)


def make_order(preparations=5):
    return ProductionOrder.create(
        recipe_id=uuid4(), recipe_name='Queso', result_product_id=uuid4(), result_product_name='Cuñapé',
        result_unit_id=uuid4(), result_unit_abbreviation='u', yield_per_preparation=Decimal('24'),
        warehouse_id=uuid4(), preparations=preparations,
        ingredients=[OrderIngredient(uuid4(), 'Queso', uuid4(), 'kg', Decimal('1.5'))])


class ProductionOrderDomainTests(TestCase):
    def test_expected_values_multiply_by_preparations(self):  # AC-01, INV-04
        order = make_order(5)
        self.assertEqual(order.expected_output, Decimal('120.0000'))
        self.assertEqual(order.expected_quantity(order.ingredients[0]), Decimal('7.5000'))
        order.change_plan(warehouse_id=order.warehouse_id, preparations=2)
        self.assertEqual(order.expected_output, Decimal('48.0000'))

    def test_preparations_must_be_a_positive_integer(self):  # AC-03, INV-01
        for bad in (0, -1, 2.5, 'abc', '', None, True, '2.5', 100000):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_preparations(bad)
            with self.subTest(create=bad), self.assertRaises(OrderValidationError):
                make_order(bad)
        self.assertEqual((parse_preparations(3), parse_preparations('3')), (3, 3))

    def test_start_sets_status_and_time_once(self):  # AC-06, INV-05, INV-07
        order = make_order()
        now = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)
        order.start(now)
        self.assertEqual((order.status, order.started_at), (OrderStatus.IN_PREPARATION, now))
        with self.assertRaises(OrderStateError):
            order.start(now)

    def test_started_order_cannot_be_edited(self):  # AC-07
        order = make_order()
        order.start(datetime.now(timezone.utc))
        with self.assertRaises(OrderStateError):
            order.change_plan(warehouse_id=uuid4(), preparations=1)


NOW = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)


def started_order():
    order = make_order(5)
    order.start(NOW - timedelta(hours=2))
    return order


class RefrigerationDomainTests(TestCase):
    def capture(self, order, **changes):
        values = {'entered_at': NOW, 'actual_output': '118',
                  'ingredients': [{'product_id': order.ingredients[0].product_id, 'actual_quantity': '7'}]}
        values.update(changes)
        return order.validate_refrigeration(now=NOW, **values)

    def test_quantities_accept_zero_only_when_allowed(self):  # INV-02
        self.assertEqual(parse_quantity('7', allow_zero=True), Decimal('7.0000'))
        self.assertEqual(parse_quantity(0, allow_zero=True), Decimal('0.0000'))
        for bad in (-1, 'x', None, True, '1.00001', float('nan'), 10 ** 13):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_quantity(bad, allow_zero=True)
        with self.assertRaises(ValueError):
            parse_quantity(0, allow_zero=False)

    def test_validation_normalises_the_capture(self):  # AC-01, INV-03
        order = started_order()
        entered, output, consumption = self.capture(order)
        self.assertEqual((entered, output), (NOW, Decimal('118.0000')))
        self.assertEqual(consumption, {order.ingredients[0].product_id: Decimal('7.0000')})

    def test_entry_time_must_be_between_start_and_now(self):  # INV-03
        order = started_order()
        for bad in (NOW - timedelta(hours=3), NOW + timedelta(minutes=6), None, datetime(2026, 11, 26, 11)):
            with self.subTest(bad=bad), self.assertRaises(OrderValidationError) as raised:
                self.capture(order, entered_at=bad)
            self.assertIn('entered_at', raised.exception.errors)
        self.capture(order, entered_at=NOW + timedelta(minutes=5))

    def test_refrigerate_moves_state_once_and_keeps_actuals(self):  # AC-02, INV-01
        order = started_order()
        line = order.ingredients[0]
        lot_id = uuid4()
        used = {line.product_id: Decimal('7')}
        order.refrigerate(now=NOW, entered_at=NOW, actual_output=Decimal('118'), consumption=used, lot_id=lot_id,
                          lot_code='L-1', cost_total=None)
        self.assertEqual((order.status, order.lot_id, order.actual_output),
                         (OrderStatus.REFRIGERATING, lot_id, Decimal('118')))
        self.assertEqual(order.ingredients[0].actual_quantity, Decimal('7'))
        self.assertEqual(order.expected_output, Decimal('120.0000'))
        with self.assertRaises(OrderStateError):
            order.refrigerate(now=NOW, entered_at=NOW, actual_output=Decimal('1'), consumption=used, lot_id=lot_id,
                              lot_code='L-1', cost_total=None)

    def test_a_draft_cannot_be_refrigerated(self):  # INV-01
        order = make_order()
        with self.assertRaises(OrderStateError):
            order.refrigerate(now=NOW, entered_at=NOW, actual_output=Decimal('1'), consumption={},
                              lot_id=uuid4(), lot_code='L', cost_total=None)
