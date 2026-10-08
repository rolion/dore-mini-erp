from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.sales.domain.enums import OrderStatus, PaymentMethod, PaymentStatus, SalesChannel
from modules.sales.domain.exceptions import OrderItemNotFound, OrderRuleViolation, OrderValidationError
from modules.sales.domain.order import Order

ORDER_DATE = date(2026, 10, 1)
TODAY = date(2026, 10, 8)
NOW = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
D = Decimal


def new_order(**overrides) -> Order:
    values = {'sales_channel': 'WHATSAPP', 'order_date': ORDER_DATE}
    values.update(overrides)
    return Order.create(**values)


def order_with_item(price='35.00', quantity=2) -> Order:
    order = new_order()
    order.add_item(uuid4(), 'Pack cuñapé', D(price), quantity)
    return order


def in_status(status: OrderStatus, price='35.00', quantity=2) -> Order:
    """Pedido con un ítem llevado a `status` por las transiciones reales."""
    order = order_with_item(price, quantity)
    if status is OrderStatus.CANCELLED:
        order.cancel('Cliente desistió', NOW)
        return order
    steps = [order.start_preparation, order.mark_ready, lambda: order.deliver(None, TODAY)]
    order_of_states = [OrderStatus.NEW, OrderStatus.IN_PREPARATION, OrderStatus.READY, OrderStatus.DELIVERED]
    for step in steps[:order_of_states.index(status)]:
        step()
    return order


def pay(order: Order, amount, method='CASH', payment_date=None, reference=''):
    return order.register_payment(amount, method, payment_date, reference, TODAY)


def violation_code(testcase, func, *args, **kwargs) -> str:
    with testcase.assertRaises(OrderRuleViolation) as ctx:
        func(*args, **kwargs)
    return ctx.exception.code


def field_errors(testcase, func, *args, **kwargs) -> dict:
    with testcase.assertRaises(OrderValidationError) as ctx:
        func(*args, **kwargs)
    return ctx.exception.errors


class CreateOrderTests(SimpleTestCase):
    def test_creates_new_order_without_items(self):  # AC-01
        order = new_order(notes='  Entregar en la tarde ')
        self.assertEqual(order.status, OrderStatus.NEW)
        self.assertEqual(order.payment_status, PaymentStatus.PENDING)
        self.assertEqual(order.items, [])
        self.assertEqual((order.subtotal, order.discount, order.total, order.balance), (D('0.00'),) * 4)
        self.assertIsNone(order.customer_id)
        self.assertIsNone(order.expected_delivery_date)
        self.assertEqual(order.notes, 'Entregar en la tarde')
        self.assertEqual(order.sales_channel, SalesChannel.WHATSAPP)

    def test_channel_is_required_and_must_be_known(self):  # AC-01, AC-08
        self.assertIn('sales_channel', field_errors(self, new_order, sales_channel=None))
        self.assertIn('sales_channel', field_errors(self, new_order, sales_channel='TELEGRAM'))
        for channel in SalesChannel:
            self.assertEqual(new_order(sales_channel=channel.value).sales_channel, channel)

    def test_all_field_errors_are_reported_together(self):  # AC-01
        errors = field_errors(self, new_order, sales_channel='X', order_date=None, notes='n' * 2001)
        self.assertEqual(set(errors), {'sales_channel', 'order_date', 'notes'})

    def test_order_date_must_be_a_date(self):  # AC-01
        self.assertIn('order_date', field_errors(self, new_order, order_date='2026-10-01'))
        self.assertIn('order_date', field_errors(self, new_order, order_date=datetime(2026, 10, 1)))

    def test_expected_delivery_cannot_precede_order_date(self):  # AC-10, EDGE-06
        self.assertIn('expected_delivery_date',
                      field_errors(self, new_order, expected_delivery_date=date(2026, 9, 30)))
        self.assertEqual(new_order(expected_delivery_date=ORDER_DATE).expected_delivery_date, ORDER_DATE)


class UpdateDetailsTests(SimpleTestCase):
    def test_partial_update_changes_only_given_fields(self):  # AC-10, AC-24
        order = new_order(notes='a')
        customer = uuid4()
        order.update_details(customer_id=customer, expected_delivery_date=date(2026, 10, 10))
        self.assertEqual(order.customer_id, customer)
        self.assertEqual(order.expected_delivery_date, date(2026, 10, 10))
        self.assertEqual((order.notes, order.sales_channel), ('a', SalesChannel.WHATSAPP))

    def test_customer_and_expected_delivery_can_be_cleared(self):
        order = new_order(customer_id=uuid4(), expected_delivery_date=date(2026, 10, 10))
        order.update_details(customer_id=None, expected_delivery_date=None)
        self.assertIsNone(order.customer_id)
        self.assertIsNone(order.expected_delivery_date)

    def test_moving_order_date_after_expected_delivery_fails_and_changes_nothing(self):  # EDGE-06
        order = new_order(expected_delivery_date=date(2026, 10, 5))
        errors = field_errors(self, order.update_details, order_date=date(2026, 10, 6), notes='x')
        self.assertIn('expected_delivery_date', errors)
        self.assertEqual((order.order_date, order.notes), (ORDER_DATE, ''))

    def test_invalid_channel_on_update(self):
        self.assertIn('sales_channel', field_errors(self, new_order().update_details, sales_channel='NOPE'))

    def test_not_editable_in_terminal_states(self):  # AC-19
        for status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            order = in_status(status)
            self.assertEqual(violation_code(self, order.update_details, notes='x'), 'order_not_editable')

    def test_editable_while_open(self):  # INV-04
        for status in (OrderStatus.NEW, OrderStatus.IN_PREPARATION, OrderStatus.READY):
            order = in_status(status)
            order.update_details(notes='cambio')
            self.assertEqual(order.notes, 'cambio')


class ItemTests(SimpleTestCase):
    def test_two_units_compute_item_subtotal_and_order_totals(self):  # AC-03, AC-06
        order = new_order()
        product = uuid4()
        item = order.add_item(product, 'Pack cuñapé', D('35.00'), 2)
        self.assertEqual(item.subtotal, D('70.00'))
        self.assertEqual((order.subtotal, order.total), (D('70.00'), D('70.00')))
        self.assertEqual((item.product_id, item.product_name, item.unit_price), (product, 'Pack cuñapé', D('35.00')))

    def test_subtotal_is_the_sum_of_items(self):  # AC-06
        order = order_with_item('35.00', 2)
        order.add_item(uuid4(), 'Chipa', D('12.50'), 3)
        self.assertEqual(order.subtotal, D('107.50'))

    def test_invalid_quantities_are_rejected(self):  # AC-03, AC-04, INV-02
        order = new_order()
        for quantity in (0, -1, 1.5, '2', True, None, 100_001):
            self.assertIn('quantity', field_errors(self, order.add_item, uuid4(), 'A', D('1.00'), quantity), quantity)
        self.assertEqual(order.items, [])

    def test_quantity_limits_are_accepted(self):  # INV-02
        order = new_order()
        order.add_item(uuid4(), 'A', D('1.00'), 1)
        order.add_item(uuid4(), 'B', D('1.00'), 100_000)

    def test_product_cannot_be_repeated(self):  # AC-03, INV-02
        order = new_order()
        product = uuid4()
        order.add_item(product, 'A', D('1.00'), 1)
        self.assertEqual(violation_code(self, order.add_item, product, 'A', D('1.00'), 1), 'duplicate_product')
        self.assertEqual(len(order.items), 1)

    def test_order_amount_cannot_exceed_the_maximum(self):  # INV-01
        order = new_order()
        self.assertIn('quantity', field_errors(self, order.add_item, uuid4(), 'Caro', D('9999999999.99'), 2))
        item = order.add_item(uuid4(), 'Caro', D('5000000000.00'), 1)
        self.assertIn('quantity', field_errors(self, order.change_item_quantity, item.id, 3))
        self.assertEqual(item.quantity, 1)

    def test_product_with_zero_price_can_be_added(self):  # INV-01, AC-03 (v2, REV-03)
        order = new_order()
        item = order.add_item(uuid4(), 'Muestra gratis', D('0.00'), 3)
        self.assertEqual((item.unit_price, item.subtotal), (D('0.00'), D('0.00')))
        self.assertEqual((order.subtotal, order.total), (D('0.00'), D('0.00')))

    def test_order_with_only_free_items_is_paid_with_no_balance(self):  # EDGE-13
        order = new_order()
        order.add_item(uuid4(), 'Muestra gratis', D('0.00'), 2)
        self.assertEqual((order.total, order.balance, order.payment_status), (D('0.00'), D('0.00'), PaymentStatus.PAID))
        self.assertFalse(order.can_register_payment)
        self.assertIn('amount', field_errors(self, pay, order, '1.00'))
        order.start_preparation()
        order.mark_ready()
        order.deliver(None, TODAY)
        self.assertEqual((order.status, order.payment_status), (OrderStatus.DELIVERED, PaymentStatus.PAID))

    def test_free_and_paid_items_mix_correctly(self):  # EDGE-13
        order = order_with_item('35.00', 2)
        order.add_item(uuid4(), 'Obsequio', D('0.00'), 1)
        self.assertEqual(order.total, D('70.00'))
        self.assertEqual(order.payment_status, PaymentStatus.PENDING)
        pay(order, '70.00')
        self.assertEqual(order.payment_status, PaymentStatus.PAID)

    def test_change_quantity_recalculates(self):  # AC-04
        order = order_with_item('35.00', 2)
        item = order.items[0]
        order.change_item_quantity(item.id, 5)
        self.assertEqual((item.subtotal, order.total), (D('175.00'), D('175.00')))

    def test_change_quantity_validates_and_finds_item(self):  # AC-04, AC-05
        order = order_with_item()
        self.assertIn('quantity', field_errors(self, order.change_item_quantity, order.items[0].id, 0))
        with self.assertRaises(OrderItemNotFound):
            order.change_item_quantity(uuid4(), 1)
        with self.assertRaises(OrderItemNotFound):
            order.remove_item(uuid4())

    def test_remove_item_recalculates(self):  # AC-05
        order = order_with_item('35.00', 2)
        second = order.add_item(uuid4(), 'Chipa', D('10.00'), 1)
        order.remove_item(second.id)
        self.assertEqual(order.total, D('70.00'))

    def test_new_order_can_be_left_without_items(self):  # AC-02
        order = order_with_item()
        order.remove_item(order.items[0].id)
        self.assertEqual((order.items, order.total, order.payment_status), ([], D('0.00'), PaymentStatus.PENDING))

    def test_confirmed_order_cannot_lose_its_last_item(self):  # AC-02, INV-06
        for status in (OrderStatus.IN_PREPARATION, OrderStatus.READY):
            order = in_status(status)
            self.assertEqual(violation_code(self, order.remove_item, order.items[0].id), 'empty_order')
            self.assertEqual(len(order.items), 1)

    def test_confirmed_order_can_remove_an_item_when_others_remain(self):  # INV-06
        order = in_status(OrderStatus.IN_PREPARATION)
        second = order.add_item(uuid4(), 'Chipa', D('10.00'), 1)
        order.remove_item(second.id)
        self.assertEqual(len(order.items), 1)

    def test_items_are_editable_until_ready_only(self):  # INV-04, AC-19
        for status in (OrderStatus.NEW, OrderStatus.IN_PREPARATION, OrderStatus.READY):
            order = in_status(status)
            order.add_item(uuid4(), 'Extra', D('1.00'), 1)
        for status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            order = in_status(status)
            self.assertEqual(violation_code(self, order.add_item, uuid4(), 'X', D('1.00'), 1), 'order_not_editable')
            self.assertEqual(violation_code(self, order.change_item_quantity, order.items[0].id, 1),
                             'order_not_editable')
            self.assertEqual(violation_code(self, order.remove_item, order.items[0].id), 'order_not_editable')
            self.assertEqual(violation_code(self, order.apply_discount, '1.00'), 'order_not_editable')


class DiscountTests(SimpleTestCase):
    def test_discount_reduces_total_and_is_explicit(self):  # AC-07
        order = order_with_item('35.00', 2)
        order.apply_discount('10.00')
        self.assertEqual((order.subtotal, order.discount, order.total), (D('70.00'), D('10.00'), D('60.00')))

    def test_discount_accepts_decimal_and_zero_removes_it(self):  # AC-07
        order = order_with_item()
        order.apply_discount(D('5.50'))
        self.assertEqual(order.total, D('64.50'))
        order.apply_discount(0)
        self.assertEqual((order.discount, order.total), (D('0.00'), D('70.00')))

    def test_discount_cannot_exceed_subtotal(self):  # AC-07, INV-03
        order = order_with_item()
        self.assertIn('discount', field_errors(self, order.apply_discount, '70.01'))
        self.assertEqual(order.discount, D('0.00'))

    def test_discount_equal_to_subtotal_is_allowed(self):  # EDGE-04
        order = order_with_item()
        order.apply_discount('70.00')
        self.assertEqual(order.total, D('0.00'))

    def test_invalid_discount_values(self):  # AC-07, INV-01
        order = order_with_item()
        for value in ('-1', 'abc', 1.5, True, None, '1.005'):
            self.assertIn('discount', field_errors(self, order.apply_discount, value), value)

    def test_discount_on_empty_order_must_be_zero(self):  # INV-03
        self.assertIn('discount', field_errors(self, new_order().apply_discount, '1.00'))

    def test_discount_cannot_leave_total_below_paid(self):  # AC-07, INV-05
        order = order_with_item('35.00', 2)
        pay(order, '65.00')
        self.assertEqual(violation_code(self, order.apply_discount, '10.00'), 'total_below_paid')
        order.apply_discount('5.00')
        self.assertEqual(order.balance, D('0.00'))

    def test_reducing_items_cannot_leave_discount_above_subtotal(self):  # AC-07
        order = order_with_item('35.00', 2)
        order.apply_discount('60.00')
        self.assertEqual(violation_code(self, order.change_item_quantity, order.items[0].id, 1),
                         'discount_exceeds_subtotal')
        self.assertEqual(order.items[0].quantity, 2)
        extra = order.add_item(uuid4(), 'Extra', D('10.00'), 1)
        order.remove_item(extra.id)
        self.assertEqual(violation_code(self, order.remove_item, order.items[0].id), 'discount_exceeds_subtotal')

    def test_reducing_items_cannot_leave_total_below_paid(self):  # AC-07, EDGE-05
        order = order_with_item('35.00', 2)
        pay(order, '40.00')
        self.assertEqual(violation_code(self, order.change_item_quantity, order.items[0].id, 1), 'total_below_paid')
        self.assertEqual(violation_code(self, order.remove_item, order.items[0].id), 'total_below_paid')
        self.assertEqual(order.items[0].quantity, 2)


class TransitionTests(SimpleTestCase):
    def test_happy_path_new_to_delivered(self):  # AC-09
        order = order_with_item()
        order.start_preparation()
        self.assertEqual(order.status, OrderStatus.IN_PREPARATION)
        order.mark_ready()
        self.assertEqual(order.status, OrderStatus.READY)
        order.deliver(None, TODAY)
        self.assertEqual((order.status, order.delivered_date), (OrderStatus.DELIVERED, TODAY))

    def test_only_valid_transitions_are_allowed(self):  # AC-09, INV-07
        actions = {
            'prepare': lambda o: o.start_preparation(),
            'ready': lambda o: o.mark_ready(),
            'deliver': lambda o: o.deliver(None, TODAY),
            'cancel': lambda o: o.cancel('motivo', NOW),
        }
        for status in OrderStatus:
            for action, run in actions.items():
                order = in_status(status)
                before = order.status
                if action in order.allowed_transitions:
                    run(order)
                    self.assertNotEqual(order.status, before, (status, action))
                else:
                    self.assertEqual(violation_code(self, run, order), 'invalid_transition', (status, action))
                    self.assertEqual(order.status, before)

    def test_allowed_transitions_by_state(self):  # AC-09
        expected = {
            OrderStatus.NEW: ['prepare', 'cancel'],
            OrderStatus.IN_PREPARATION: ['ready', 'cancel'],
            OrderStatus.READY: ['deliver', 'cancel'],
            OrderStatus.DELIVERED: [],
            OrderStatus.CANCELLED: [],
        }
        for status, transitions in expected.items():
            self.assertEqual(in_status(status).allowed_transitions, transitions)

    def test_cancelled_order_cannot_be_delivered(self):  # AC-09
        order = in_status(OrderStatus.CANCELLED)
        self.assertEqual(violation_code(self, order.deliver, None, TODAY), 'invalid_transition')
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_delivered_order_cannot_return_or_be_cancelled(self):  # AC-09
        order = in_status(OrderStatus.DELIVERED)
        self.assertEqual(violation_code(self, order.start_preparation), 'invalid_transition')
        self.assertEqual(violation_code(self, order.cancel, 'tarde', NOW), 'invalid_transition')

    def test_preparation_requires_an_item(self):  # AC-02
        order = new_order()
        self.assertEqual(violation_code(self, order.start_preparation), 'empty_order')
        self.assertEqual(order.status, OrderStatus.NEW)

    def test_editable_flag_follows_status(self):  # INV-04
        flags = {s: in_status(s).editable for s in OrderStatus}
        self.assertEqual(flags, {OrderStatus.NEW: True, OrderStatus.IN_PREPARATION: True, OrderStatus.READY: True,
                                 OrderStatus.DELIVERED: False, OrderStatus.CANCELLED: False})


class DeliveryDateTests(SimpleTestCase):
    def test_actual_delivery_date_can_be_given(self):  # AC-10
        order = in_status(OrderStatus.READY)
        order.deliver(date(2026, 10, 5), TODAY)
        self.assertEqual(order.delivered_date, date(2026, 10, 5))

    def test_actual_delivery_cannot_be_future_or_before_order_date(self):  # AC-10, EDGE-07
        for bad in (date(2026, 10, 9), date(2026, 9, 30)):
            order = in_status(OrderStatus.READY)
            self.assertIn('delivered_date', field_errors(self, order.deliver, bad, TODAY))
            self.assertEqual((order.status, order.delivered_date), (OrderStatus.READY, None))

    def test_actual_delivery_must_be_a_date(self):  # AC-10
        order = in_status(OrderStatus.READY)
        self.assertIn('delivered_date', field_errors(self, order.deliver, '2026-10-05', TODAY))


class CancelTests(SimpleTestCase):
    def test_cancel_requires_a_reason(self):  # AC-11
        for reason in (None, '', '   ', 'x' * 501):
            order = order_with_item()
            self.assertIn('reason', field_errors(self, order.cancel, reason, NOW), repr(reason))
            self.assertEqual(order.status, OrderStatus.NEW)

    def test_cancel_open_orders_keeps_everything(self):  # AC-11, INV-08
        for status in (OrderStatus.NEW, OrderStatus.IN_PREPARATION, OrderStatus.READY):
            order = in_status(status)
            pay(order, '20.00')
            order.cancel('  Cliente desistió ', NOW)
            self.assertEqual(order.status, OrderStatus.CANCELLED)
            self.assertEqual((order.cancellation_reason, order.cancelled_at), ('Cliente desistió', NOW))
            self.assertEqual((len(order.items), len(order.payments)), (1, 1))
            self.assertEqual(order.payment_status, PaymentStatus.PARTIAL)
            self.assertEqual(order.balance, D('50.00'))

    def test_cancelled_order_exposes_no_actions(self):  # AC-11
        order = in_status(OrderStatus.CANCELLED)
        self.assertEqual((order.editable, order.allowed_transitions, order.can_register_payment),
                         (False, [], False))

    def test_cancelled_order_rejects_new_payments(self):  # AC-12, EDGE-11
        order = in_status(OrderStatus.CANCELLED)
        self.assertEqual(violation_code(self, pay, order, '1.00'), 'order_cancelled')


class PaymentTests(SimpleTestCase):
    def test_payment_increases_paid_total_and_is_listed(self):  # AC-12
        order = order_with_item()
        payment = pay(order, '20.00', 'QR', date(2026, 10, 2), ' ref-1 ')
        self.assertEqual(order.payments, [payment])
        self.assertEqual((order.paid_total, order.balance), (D('20.00'), D('50.00')))
        self.assertEqual((payment.payment_method, payment.payment_date, payment.reference),
                         (PaymentMethod.QR, date(2026, 10, 2), 'ref-1'))

    def test_payment_date_defaults_to_today(self):  # AC-12
        self.assertEqual(pay(order_with_item(), '1.00').payment_date, TODAY)

    def test_amount_must_be_positive_decimal(self):  # AC-12, INV-10
        order = order_with_item()
        for value in (0, '0.00', '-5', 'abc', 1.5, True, None, '1.005'):
            self.assertIn('amount', field_errors(self, pay, order, value), repr(value))
        self.assertEqual(order.payments, [])

    def test_amount_cannot_exceed_balance(self):  # AC-12, INV-10
        order = order_with_item()
        self.assertIn('amount', field_errors(self, pay, order, '70.01'))
        pay(order, '70.00')
        self.assertIn('amount', field_errors(self, pay, order, '0.01'))
        self.assertEqual(len(order.payments), 1)

    def test_method_date_and_reference_are_validated_together(self):  # AC-12
        order = order_with_item()
        errors = field_errors(self, pay, order, '1.00', 'BITCOIN', date(2026, 10, 9), 'r' * 101)
        self.assertEqual(set(errors), {'payment_method', 'payment_date', 'reference'})

    def test_methods_accepted(self):  # AC-12
        order = order_with_item('100.00', 1)
        for method in PaymentMethod:
            pay(order, '1.00', method.value)
        self.assertEqual(len(order.payments), 5)

    def test_payment_allowed_in_every_open_state_and_delivered_with_balance(self):  # AC-12, AC-15
        for status in (OrderStatus.NEW, OrderStatus.IN_PREPARATION, OrderStatus.READY, OrderStatus.DELIVERED):
            order = in_status(status)
            self.assertTrue(order.can_register_payment)
            pay(order, '10.00')

    def test_payment_requires_existing_balance(self):  # EDGE-04
        order = order_with_item()
        order.apply_discount('70.00')
        self.assertFalse(order.can_register_payment)
        self.assertIn('amount', field_errors(self, pay, order, '1.00'))

    def test_empty_order_accepts_no_payment(self):  # INV-10
        self.assertIn('amount', field_errors(self, pay, new_order(), '1.00'))


class PaymentStatusTests(SimpleTestCase):
    def test_pending_partial_paid(self):  # AC-13
        order = order_with_item('35.00', 2)
        self.assertEqual(order.payment_status, PaymentStatus.PENDING)
        pay(order, '20.00')
        self.assertEqual(order.payment_status, PaymentStatus.PARTIAL)
        pay(order, '50.00')
        self.assertEqual((order.payment_status, order.balance), (PaymentStatus.PAID, D('0.00')))

    def test_order_without_items_is_pending(self):  # AC-13
        self.assertEqual(new_order().payment_status, PaymentStatus.PENDING)

    def test_full_discount_with_items_is_paid(self):  # AC-13, EDGE-04
        order = order_with_item()
        order.apply_discount('70.00')
        self.assertEqual((order.total, order.payment_status), (D('0.00'), PaymentStatus.PAID))

    def test_status_follows_total_when_items_change(self):  # AC-13
        order = order_with_item('35.00', 2)
        pay(order, '35.00')
        self.assertEqual(order.payment_status, PaymentStatus.PARTIAL)
        order.add_item(uuid4(), 'Extra', D('10.00'), 1)
        self.assertEqual(order.payment_status, PaymentStatus.PARTIAL)
        order.remove_item(order.items[1].id)
        order.change_item_quantity(order.items[0].id, 1)
        self.assertEqual(order.payment_status, PaymentStatus.PAID)

    def test_refunded_is_never_derived(self):  # INV-11
        order = in_status(OrderStatus.CANCELLED)
        pay_status = {in_status(s).payment_status for s in OrderStatus}
        self.assertNotIn(PaymentStatus.REFUNDED, pay_status | {order.payment_status})


class DeliveryAndPaymentAreIndependentTests(SimpleTestCase):
    def test_delivered_with_pending_balance(self):  # AC-14, AC-15
        order = in_status(OrderStatus.DELIVERED)
        self.assertEqual((order.status, order.payment_status), (OrderStatus.DELIVERED, PaymentStatus.PENDING))
        self.assertEqual(order.balance, D('70.00'))
        pay(order, '30.00')
        self.assertEqual((order.status, order.payment_status), (OrderStatus.DELIVERED, PaymentStatus.PARTIAL))
        self.assertEqual(order.balance, D('40.00'))

    def test_paid_before_delivery(self):  # AC-14, AC-15
        order = order_with_item()
        pay(order, '70.00')
        self.assertEqual((order.status, order.payment_status, order.balance),
                         (OrderStatus.NEW, PaymentStatus.PAID, D('0.00')))
        order.start_preparation()
        order.mark_ready()
        self.assertEqual(order.payment_status, PaymentStatus.PAID)
        order.deliver(None, TODAY)
        self.assertEqual((order.status, order.payment_status), (OrderStatus.DELIVERED, PaymentStatus.PAID))

    def test_balance_is_total_minus_valid_payments_regardless_of_status(self):  # AC-14
        for status in OrderStatus:
            order = in_status(status)
            self.assertEqual(order.balance, order.total - order.paid_total)
