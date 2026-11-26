from datetime import datetime, timezone
from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from modules.production.domain.production_order import (
    OrderIngredient, OrderStateError, OrderStatus, OrderValidationError, ProductionOrder, parse_preparations)


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
