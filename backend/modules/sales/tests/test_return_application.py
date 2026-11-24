"""Devolución total y cancelación con reembolso: casos de uso con dobles en memoria (sin base de datos)."""
from uuid import uuid4

from modules.sales.application.commands import DeliverOrder, MarkOrderReady, RegisterPayment, StartOrderPreparation
from modules.sales.application.ports import Actor
from modules.sales.application.returns import PreviewOrderReturn, ReturnOrder
from modules.sales.domain.enums import OrderStatus, PaymentStatus
from modules.sales.domain.exceptions import OrderNotFound, OrderRuleViolation

from .fakes import FixedClock
from .test_application import ApplicationTestCase
from .test_delivery_application import FakeStock
from .test_sales_posting_application import FakePosting


class FakeCosting:
    def __init__(self):
        self.reversed = []

    def reverse_cost(self, order_id):
        self.reversed.append(order_id)


class ReturnApplicationTests(ApplicationTestCase):
    def setUp(self):
        super().setUp()
        self.stock, self.costing, self.posting = FakeStock(), FakeCosting(), FakePosting()
        self.actor = Actor(uuid4(), 'ana')

    def delivered(self, paid=None):
        order = self.add_item(self.create(), self.products.add(price='100.00'), 2)
        StartOrderPreparation(self.repository).execute(order.id)
        MarkOrderReady(self.repository).execute(order.id)
        if paid:
            RegisterPayment(self.repository, self.clock).execute(order.id, paid, 'CASH', None, '')
        return DeliverOrder(self.repository, FixedClock()).execute(order.id)

    def use_case(self):
        return ReturnOrder(self.repository, FixedClock(), self.stock, self.posting, self.costing)

    def test_return_reverses_stock_cost_and_entries_and_saves_once(self):  # AC-03, AC-04, AC-05
        order = self.delivered()
        saves = self.repository.saves
        returned = self.use_case().execute(order.id, 'Defectuoso', self.actor)
        self.assertEqual((returned.status, returned.return_reason, returned.returned_by_name),
                         (OrderStatus.RETURNED, 'Defectuoso', 'ana'))
        self.assertEqual(self.stock.reversed, [(order.id, 'Defectuoso', self.actor)])
        self.assertEqual(self.costing.reversed, [order.id])
        self.assertEqual(self.posting.calls, [('reverse_delivery', 'Defectuoso')])
        self.assertEqual(self.repository.saves, saves + 1)

    def test_with_payments_the_refund_is_required_and_then_counterposted(self):  # AC-02
        order = self.delivered(paid='50.00')
        with self.assertRaises(OrderRuleViolation) as caught:
            self.use_case().execute(order.id, 'Defectuoso', self.actor)
        self.assertEqual(caught.exception.code, 'refund_acknowledgement_required')
        self.assertEqual((self.stock.reversed, self.posting.calls), ([], []))
        returned = self.use_case().execute(order.id, 'Defectuoso', self.actor, refund_acknowledged=True)
        self.assertEqual((returned.payment_status, returned.refund_acknowledged), (PaymentStatus.REFUNDED, True))
        self.assertEqual([call[0] for call in self.posting.calls], ['reverse_delivery', 'reverse_payments'])

    def test_a_failure_in_any_step_does_not_save_the_order(self):  # AC-06
        order = self.delivered()
        self.posting.reverse_delivery = lambda *args: (_ for _ in ()).throw(
            OrderRuleViolation('fiscal_period_unavailable', 'Período cerrado'))
        saves = self.repository.saves
        with self.assertRaises(OrderRuleViolation):
            self.use_case().execute(order.id, 'Defectuoso', self.actor)
        self.assertEqual((self.repository.saves, self.repository.get(order.id).status), (saves, OrderStatus.DELIVERED))

    def test_a_second_attempt_is_rejected_without_new_effects(self):  # AC-07
        order = self.delivered()
        self.use_case().execute(order.id, 'Defectuoso', self.actor)
        with self.assertRaises(OrderRuleViolation) as caught:
            self.use_case().execute(order.id, 'Defectuoso', self.actor)
        self.assertEqual(caught.exception.code, 'invalid_transition')
        self.assertEqual((len(self.stock.reversed), len(self.costing.reversed), len(self.posting.calls)), (1, 1, 1))

    def test_only_delivered_orders_can_be_returned(self):  # INV-01
        order = self.confirmed()
        with self.assertRaises(OrderRuleViolation) as caught:
            self.use_case().execute(order.id, 'x', self.actor)
        self.assertEqual(caught.exception.code, 'invalid_transition')

    def test_works_without_inventory_costing_or_accounting(self):  # INV-04
        order = self.delivered()
        returned = ReturnOrder(self.repository, FixedClock()).execute(order.id, 'Defectuoso', self.actor)
        self.assertEqual(returned.status, OrderStatus.RETURNED)

    def test_preview_changes_nothing_and_flags_the_refund(self):  # AC-11
        order = self.delivered(paid='10.00')
        saves = self.repository.saves
        preview = PreviewOrderReturn(self.repository, self.stock, self.posting).execute(order.id)
        self.assertEqual((preview.requires_refund_acknowledgement, preview.order.id), (True, order.id))
        self.assertEqual((self.repository.saves, self.stock.reversed, self.posting.calls), (saves, [], []))
        self.assertEqual(self.repository.get(order.id).status, OrderStatus.DELIVERED)

    def test_preview_of_a_not_delivered_or_unknown_order_fails(self):  # AC-11
        with self.assertRaises(OrderRuleViolation):
            PreviewOrderReturn(self.repository).execute(self.confirmed().id)
        with self.assertRaises(OrderNotFound):
            PreviewOrderReturn(self.repository).execute(uuid4())
