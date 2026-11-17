"""VEN-01: orden y efectos de los comandos con un doble en memoria del puerto `SalesPosting` (sin base de datos)."""
from uuid import uuid4

from django.test import SimpleTestCase

from modules.sales.application.commands import (
    AddOrderItem,
    ApplyOrderDiscount,
    CancelOrder,
    CreateOrder,
    DeliverOrder,
    MarkOrderReady,
    RegisterPayment,
    StartOrderPreparation,
)
from modules.sales.application.ports import AT_CONFIRM, AT_DELIVERY
from modules.sales.domain.exceptions import OrderRuleViolation
from modules.sales.tests.fakes import FakeCustomers, FakeProducts, FixedClock, InMemoryOrderRepository


class FakePosting:
    def __init__(self, state=None, locked=False, posted_payments=False, error=None):
        self.state, self.locked, self.posted_payments, self.error, self.calls = state, locked, posted_payments, error, []

    def recognition_state(self, order_id):
        return self.state

    def locks_total(self, order):
        return self.locked

    def has_posted_payments(self, order):
        return self.posted_payments

    def record_payment(self, order, payment, actor, today):
        self.calls.append(('payment', payment.amount))
        if self.error:
            raise self.error

    def recognize_delivery(self, order, actor):
        self.calls.append(('delivery', order.status.value))
        if self.error:
            raise self.error

    def reverse_recognition(self, order, reason, actor, today):
        self.calls.append(('reverse', reason))


class PostingCommandsTests(SimpleTestCase):
    def setUp(self):
        self.repository, self.clock, self.products = InMemoryOrderRepository(), FixedClock(), FakeProducts()
        order = CreateOrder(self.repository, FakeCustomers(), self.clock).execute('WHATSAPP')
        self.order_id = order.id
        AddOrderItem(self.repository, self.products).execute(order.id, self.products.add(price='100.00').id, 3)

    def ready(self):
        StartOrderPreparation(self.repository).execute(self.order_id)
        MarkOrderReady(self.repository).execute(self.order_id)

    def test_confirming_takes_no_posting_port(self):  # AC-03
        order = StartOrderPreparation(self.repository).execute(self.order_id)
        self.assertEqual(order.status.value, 'IN_PREPARATION')

    def test_delivering_recognizes_after_the_state_change_and_saves_once(self):  # AC-05
        self.ready()
        posting = FakePosting()
        saves = self.repository.saves
        DeliverOrder(self.repository, self.clock, None, posting).execute(self.order_id)
        self.assertEqual(posting.calls, [('delivery', 'DELIVERED')])
        self.assertEqual(self.repository.saves, saves + 1)

    def test_a_posting_error_leaves_the_order_undelivered(self):  # AC-14
        self.ready()
        posting = FakePosting(error=OrderRuleViolation('posting_configuration_missing', 'Falta'))
        saves = self.repository.saves
        with self.assertRaises(OrderRuleViolation):
            DeliverOrder(self.repository, self.clock, None, posting).execute(self.order_id)
        self.assertEqual((self.repository.saves, self.repository.get(self.order_id).status.value),
                         (saves, 'READY'))

    def test_a_payment_goes_through_the_posting_port_and_a_replay_does_not(self):  # AC-08
        self.ready()
        posting, key = FakePosting(), uuid4()
        command = RegisterPayment(self.repository, self.clock, posting)
        command.execute(self.order_id, '10.00', 'CASH', None, '', key)
        command.execute(self.order_id, '10.00', 'CASH', None, '', key)
        self.assertEqual(len(posting.calls), 1)

    def test_cancel_reverses_only_the_recognition_at_confirm_and_only_without_payments(self):  # AC-10, AC-11
        StartOrderPreparation(self.repository).execute(self.order_id)
        posting = FakePosting(state=AT_CONFIRM)
        CancelOrder(self.repository, self.clock, posting).execute(self.order_id, 'Error')
        self.assertEqual([call[0] for call in posting.calls], ['reverse'])

    def test_cancel_without_recognition_posts_nothing(self):  # AC-11
        StartOrderPreparation(self.repository).execute(self.order_id)
        posting = FakePosting(state=None)
        CancelOrder(self.repository, self.clock, posting).execute(self.order_id, 'Error')
        self.assertEqual(posting.calls, [])

    def test_cancel_is_rejected_when_a_payment_is_posted(self):  # AC-11
        StartOrderPreparation(self.repository).execute(self.order_id)
        for state in (None, AT_CONFIRM, AT_DELIVERY):
            posting = FakePosting(state=state, posted_payments=True)
            with self.assertRaises(OrderRuleViolation) as caught:
                CancelOrder(self.repository, self.clock, posting).execute(self.order_id, 'Error')
            self.assertEqual(caught.exception.code, 'order_has_payments_posted')
        self.assertEqual(self.repository.get(self.order_id).status.value, 'IN_PREPARATION')

    def test_the_total_is_locked_only_when_the_port_says_so(self):  # AC-12
        StartOrderPreparation(self.repository).execute(self.order_id)
        product = self.products.add(name='Otro', price='10.00')
        with self.assertRaises(OrderRuleViolation) as caught:
            AddOrderItem(self.repository, self.products, FakePosting(locked=True)).execute(self.order_id, product.id, 1)
        self.assertEqual(caught.exception.code, 'order_total_locked')
        with self.assertRaises(OrderRuleViolation):
            ApplyOrderDiscount(self.repository, None, FakePosting(locked=True)).execute(self.order_id, '5.00')
        AddOrderItem(self.repository, self.products, FakePosting(locked=False)).execute(self.order_id, product.id, 1)
