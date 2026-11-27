"""Numeración correlativa de pedidos (TASK-numeracion-correlativa-pedidos-venta): dominio y casos de uso sin BD."""
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from django.test import SimpleTestCase

from modules.sales.application.commands import StartOrderPreparation
from modules.sales.domain.enums import OrderStatus
from modules.sales.domain.exceptions import OrderRuleViolation
from modules.sales.domain.order import Order, OrderNumber, order_code

from .fakes import NOW, FakeOrderNumbering, InMemoryOrderRepository

PERIOD = UUID('00000000-0000-4000-8000-0000000000aa')


def new_order(with_item=True, order_date=date(2026, 8, 3)) -> Order:
    order = Order.create('WHATSAPP', order_date)
    if with_item:
        order.add_item(uuid4(), 'Pack', Decimal('35.00'), 2)
    return order


class OrderNumberTests(SimpleTestCase):
    def test_code_uses_nv_prefix_with_six_digits(self):  # AC-01
        self.assertEqual(OrderNumber(PERIOD, '2026', 1).code, 'NV-000001')
        self.assertEqual(OrderNumber(PERIOD, '2026', 123456).code, 'NV-123456')

    def test_code_keeps_growing_past_six_digits(self):  # EDGE-04
        self.assertEqual(OrderNumber(PERIOD, '2026', 1_000_000).code, 'NV-1000000')

    def test_an_unconfirmed_order_shows_the_provisional_label(self):  # AC-02
        order = new_order()
        self.assertIsNone(order.number)
        self.assertEqual(order.code, order_code(order.id))
        self.assertTrue(order.code.startswith('P-'))

    def test_confirming_assigns_the_number_and_the_code(self):  # AC-01, INV-04
        order = new_order()
        order.start_preparation(OrderNumber(PERIOD, 'Gestión 2026', 7))
        self.assertEqual((order.status, order.code, order.number.period_name),
                         (OrderStatus.IN_PREPARATION, 'NV-000007', 'Gestión 2026'))

    def test_cancelling_keeps_the_number(self):  # AC-03, INV-03
        order = new_order()
        order.start_preparation(OrderNumber(PERIOD, '2026', 3))
        order.cancel('Cliente desistió', NOW)
        self.assertEqual((order.status, order.code), (OrderStatus.CANCELLED, 'NV-000003'))

    def test_a_second_confirmation_does_not_change_the_number(self):  # EDGE-01, INV-03
        order = new_order()
        first = OrderNumber(PERIOD, '2026', 1)
        order.start_preparation(first)
        with self.assertRaises(OrderRuleViolation) as caught:
            order.start_preparation(OrderNumber(PERIOD, '2026', 2))
        self.assertEqual(caught.exception.code, 'invalid_transition')
        self.assertEqual(order.number, first)

    def test_an_empty_order_is_not_numbered(self):  # INV-06
        order = new_order(with_item=False)
        with self.assertRaises(OrderRuleViolation) as caught:
            order.ensure_confirmable()
        self.assertEqual(caught.exception.code, 'empty_order')
        self.assertIsNone(order.number)


class StartOrderPreparationNumberingTests(SimpleTestCase):
    def setUp(self):
        self.repository = InMemoryOrderRepository()

    def store(self, order):
        return self.repository.save(order)

    def test_confirming_numbers_with_the_period_of_the_order_date(self):  # AC-04
        numbering = FakeOrderNumbering()
        order = self.store(new_order(order_date=date(2026, 12, 30)))
        confirmed = StartOrderPreparation(self.repository, numbering).execute(order.id)
        self.assertEqual(numbering.calls, [date(2026, 12, 30)])
        self.assertTrue(confirmed.code.startswith('NV-'))
        self.assertEqual(self.repository.get(order.id).number, confirmed.number)

    def test_a_missing_or_closed_period_leaves_the_order_new_and_unsaved(self):  # AC-05, AC-06
        for code in ('fiscal_period_missing', 'fiscal_period_closed'):
            repository = InMemoryOrderRepository()
            order = repository.save(new_order())
            saves = repository.saves
            numbering = FakeOrderNumbering(error=OrderRuleViolation(code, 'sin período'))
            with self.assertRaises(OrderRuleViolation) as caught:
                StartOrderPreparation(repository, numbering).execute(order.id)
            self.assertEqual(caught.exception.code, code)
            stored = repository.get(order.id)
            self.assertEqual((stored.status, stored.number, repository.saves), (OrderStatus.NEW, None, saves))

    def test_an_invalid_confirmation_does_not_consume_a_number(self):  # EDGE-01, INV-02
        numbering = FakeOrderNumbering()
        order = self.store(new_order(with_item=False))
        with self.assertRaises(OrderRuleViolation):
            StartOrderPreparation(self.repository, numbering).execute(order.id)
        self.assertEqual(numbering.calls, [])
