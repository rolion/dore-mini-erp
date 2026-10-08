from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.sales.application.commands import (
    AddOrderItem,
    ApplyOrderDiscount,
    CancelOrder,
    ChangeOrderItemQuantity,
    CreateOrder,
    DeliverOrder,
    MarkOrderReady,
    RegisterPayment,
    RemoveOrderItem,
    StartOrderPreparation,
    UpdateOrder,
)
from modules.sales.application.queries import GetOrder, ListOrders
from modules.sales.domain.enums import OrderStatus, PaymentStatus
from modules.sales.domain.exceptions import OrderNotFound, OrderRuleViolation, OrderValidationError

from .fakes import NOW, TODAY, FakeCustomers, FakeProducts, FixedClock, InMemoryOrderRepository

D = Decimal


class ApplicationTestCase(SimpleTestCase):
    def setUp(self):
        self.repository = InMemoryOrderRepository()
        self.products = FakeProducts()
        self.customers = FakeCustomers()
        self.clock = FixedClock()

    def create(self, **kwargs):
        kwargs.setdefault('sales_channel', 'WHATSAPP')
        return CreateOrder(self.repository, self.customers, self.clock).execute(**kwargs)

    def add_item(self, order, product=None, quantity=2):
        product = product or self.products.add()
        return AddOrderItem(self.repository, self.products).execute(order.id, product.id, quantity)

    def confirmed(self):
        order = self.add_item(self.create())
        return StartOrderPreparation(self.repository).execute(order.id)


class CreateOrderTests(ApplicationTestCase):
    def test_creates_and_persists_with_today_as_default_date(self):  # AC-01
        order = self.create()
        self.assertEqual((order.status, order.order_date), (OrderStatus.NEW, TODAY))
        self.assertEqual(self.repository.get(order.id).id, order.id)

    def test_active_customer_can_be_assigned(self):  # AC-18
        customer = self.customers.add()
        self.assertEqual(self.create(customer_id=customer.id).customer_id, customer.id)

    def test_unknown_and_inactive_customers_are_rejected(self):  # AC-18
        inactive = self.customers.add(active=False)
        for customer_id in (uuid4(), inactive.id):
            with self.assertRaises(OrderValidationError) as ctx:
                self.create(customer_id=customer_id)
            self.assertIn('customer_id', ctx.exception.errors)
        self.assertEqual(self.repository.orders, {})

    def test_customer_and_field_errors_are_reported_together(self):  # AC-18
        with self.assertRaises(OrderValidationError) as ctx:
            self.create(sales_channel='X', customer_id=uuid4())
        self.assertEqual(set(ctx.exception.errors), {'sales_channel', 'customer_id'})


class UpdateOrderTests(ApplicationTestCase):
    def test_customer_is_validated_only_when_it_changes(self):  # AC-18, INV-14
        customer = self.customers.add()
        order = self.create(customer_id=customer.id)
        self.customers.items[customer.id] = self.customers.items[customer.id].__class__(
            id=customer.id, name=customer.name, active=False)
        updated = UpdateOrder(self.repository, self.customers).execute(order.id, notes='sigue editable')
        self.assertEqual(updated.notes, 'sigue editable')
        same_customer = UpdateOrder(self.repository, self.customers).execute(order.id, customer_id=customer.id)
        self.assertEqual(same_customer.customer_id, customer.id)

    def test_changing_to_an_inactive_customer_is_rejected(self):  # AC-18
        order = self.create()
        inactive = self.customers.add(active=False)
        with self.assertRaises(OrderValidationError) as ctx:
            UpdateOrder(self.repository, self.customers).execute(order.id, customer_id=inactive.id)
        self.assertIn('customer_id', ctx.exception.errors)
        self.assertIsNone(self.repository.get(order.id).customer_id)

    def test_customer_can_be_cleared(self):  # AC-18
        order = self.create(customer_id=self.customers.add().id)
        updated = UpdateOrder(self.repository, self.customers).execute(order.id, customer_id=None)
        self.assertIsNone(updated.customer_id)

    def test_unknown_order(self):  # AC-17
        with self.assertRaises(OrderNotFound):
            UpdateOrder(self.repository, self.customers).execute(uuid4(), notes='x')

    def test_delivered_order_is_not_editable(self):  # AC-19
        order = self.confirmed()
        MarkOrderReady(self.repository).execute(order.id)
        DeliverOrder(self.repository, self.clock).execute(order.id)
        with self.assertRaises(OrderRuleViolation) as ctx:
            UpdateOrder(self.repository, self.customers).execute(order.id, notes='x')
        self.assertEqual(ctx.exception.code, 'order_not_editable')


class AddOrderItemTests(ApplicationTestCase):
    def test_snapshot_comes_from_the_catalog_and_totals_are_computed(self):  # AC-03, INV-13
        product = self.products.add(name='Pack 10 cuñapés', price='35.00')
        order = self.add_item(self.create(), product, 2)
        item = order.items[0]
        self.assertEqual((item.product_name, item.unit_price, item.subtotal), ('Pack 10 cuñapés', D('35.00'), D('70.00')))
        self.assertEqual(order.total, D('70.00'))

    def test_later_price_changes_do_not_alter_the_snapshot(self):  # EDGE-02
        product = self.products.add(price='35.00')
        order = self.add_item(self.create(), product, 1)
        self.products.items[product.id] = product.__class__(id=product.id, name='Nuevo nombre',
                                                            sale_price=D('99.00'), active=True)
        self.assertEqual(self.repository.get(order.id).items[0].unit_price, D('35.00'))
        self.assertEqual(self.repository.get(order.id).items[0].product_name, 'Pack cuñapé')

    def test_inactive_unknown_products_are_rejected(self):  # AC-03
        order = self.create()
        inactive = self.products.add(active=False)
        for product_id in (inactive.id, uuid4()):
            with self.assertRaises(OrderValidationError) as ctx:
                AddOrderItem(self.repository, self.products).execute(order.id, product_id, 1)
            self.assertIn('product_id', ctx.exception.errors)
        self.assertEqual(self.repository.get(order.id).items, [])

    def test_product_and_quantity_errors_are_reported_together(self):  # AC-03
        order = self.create()
        with self.assertRaises(OrderValidationError) as ctx:
            AddOrderItem(self.repository, self.products).execute(order.id, uuid4(), 0)
        self.assertEqual(set(ctx.exception.errors), {'product_id', 'quantity'})

    def test_not_editable_has_priority_over_input_errors(self):  # AC-19
        order = self.create()
        CancelOrder(self.repository, self.clock).execute(order.id, 'motivo')
        with self.assertRaises(OrderRuleViolation) as ctx:
            AddOrderItem(self.repository, self.products).execute(order.id, uuid4(), 0)
        self.assertEqual(ctx.exception.code, 'order_not_editable')

    def test_free_products_can_be_added(self):  # AC-03 (v2, REV-03)
        gift = self.products.add(name='Obsequio', price='0.00')
        order = self.add_item(self.create(), gift, 2)
        self.assertEqual((order.items[0].unit_price, order.total, order.payment_status),
                         (D('0.00'), D('0.00'), PaymentStatus.PAID))

    def test_duplicate_product(self):  # AC-03
        product = self.products.add()
        order = self.add_item(self.create(), product)
        with self.assertRaises(OrderRuleViolation) as ctx:
            self.add_item(order, product)
        self.assertEqual(ctx.exception.code, 'duplicate_product')

    def test_inactivated_product_stays_in_the_order(self):  # EDGE-03
        product = self.products.add()
        order = self.add_item(self.create(), product, 1)
        self.products.items[product.id] = product.__class__(id=product.id, name=product.name,
                                                            sale_price=product.sale_price, active=False)
        changed = ChangeOrderItemQuantity(self.repository).execute(order.id, order.items[0].id, 3)
        self.assertEqual(changed.items[0].quantity, 3)


class WorkflowTests(ApplicationTestCase):
    def test_full_cycle_with_partial_payments(self):  # AC-09, AC-12, AC-13, AC-15
        order = self.add_item(self.create(), quantity=2)
        ApplyOrderDiscount(self.repository).execute(order.id, '10.00')
        order = StartOrderPreparation(self.repository).execute(order.id)
        order = MarkOrderReady(self.repository).execute(order.id)
        order = DeliverOrder(self.repository, self.clock).execute(order.id)
        self.assertEqual((order.status, order.delivered_date, order.total), (OrderStatus.DELIVERED, TODAY, D('60.00')))
        self.assertEqual(order.payment_status, PaymentStatus.PENDING)
        pay = RegisterPayment(self.repository, self.clock)
        order = pay.execute(order.id, '25.00', 'QR')
        self.assertEqual((order.payment_status, order.balance), (PaymentStatus.PARTIAL, D('35.00')))
        order = pay.execute(order.id, '35.00', 'CASH', date(2026, 10, 7), 'recibo 1')
        self.assertEqual((order.payment_status, order.balance, len(order.payments)), (PaymentStatus.PAID, D('0.00'), 2))

    def test_failed_operations_do_not_persist(self):  # AC-02, AC-09
        order = self.create()
        saves = self.repository.saves
        with self.assertRaises(OrderRuleViolation):
            StartOrderPreparation(self.repository).execute(order.id)
        with self.assertRaises(OrderRuleViolation):
            MarkOrderReady(self.repository).execute(order.id)
        self.assertEqual(self.repository.saves, saves)

    def test_cancel_uses_clock_and_requires_reason(self):  # AC-11
        order = self.create()
        with self.assertRaises(OrderValidationError):
            CancelOrder(self.repository, self.clock).execute(order.id, ' ')
        cancelled = CancelOrder(self.repository, self.clock).execute(order.id, 'No lo quiere')
        self.assertEqual((cancelled.status, cancelled.cancelled_at), (OrderStatus.CANCELLED, NOW))

    def test_remove_item_and_quantity_use_the_aggregate_rules(self):  # AC-04, AC-05
        order = self.add_item(self.create(), quantity=2)
        item_id = order.items[0].id
        order = ChangeOrderItemQuantity(self.repository).execute(order.id, item_id, 4)
        self.assertEqual(order.total, D('140.00'))
        order = RemoveOrderItem(self.repository).execute(order.id, item_id)
        self.assertEqual(order.total, D('0.00'))

    def test_unknown_order_raises_not_found(self):  # AC-17
        for call in (
            lambda: StartOrderPreparation(self.repository).execute(uuid4()),
            lambda: RegisterPayment(self.repository, self.clock).execute(uuid4(), '1.00', 'CASH'),
            lambda: GetOrder(self.repository).execute(uuid4()),
        ):
            with self.assertRaises(OrderNotFound):
                call()


class QueryTests(ApplicationTestCase):
    def test_get_and_list(self):  # AC-16, AC-17
        order = self.create()
        self.assertEqual(GetOrder(self.repository).execute(order.id).id, order.id)
        self.assertEqual([o.id for o in ListOrders(self.repository).execute()], [order.id])
