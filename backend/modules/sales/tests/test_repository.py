from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from django.db import IntegrityError, connection, transaction
from django.db.models import F
from django.db.transaction import TransactionManagementError
from django.test import TestCase, TransactionTestCase

from modules.sales.domain.enums import OrderStatus, PaymentMethod, PaymentStatus, SalesChannel
from modules.sales.domain.order import Order
from modules.sales.domain.repositories import (
    BY_EXPECTED_DELIVERY,
    NEWEST_FIRST,
    OrderFilters,
)
from modules.sales.infrastructure.django.models import OrderItemModel, OrderModel, PaymentModel
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository

D = Decimal
TODAY = date(2026, 10, 8)
NOW = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)


def make_order(order_date=date(2026, 10, 1), channel='WHATSAPP', items=(('Pack', '35.00', 2),), **kwargs) -> Order:
    order = Order.create(sales_channel=channel, order_date=order_date, **kwargs)
    for name, price, quantity in items:
        order.add_item(uuid4(), name, D(price), quantity)
    return order


class RepositoryTestCase(TestCase):
    def setUp(self):
        self.repository = DjangoOrderRepository()

    def store(self, order: Order) -> Order:
        return self.repository.save(order)


class RoundTripTests(RepositoryTestCase):
    def test_saves_and_loads_the_whole_aggregate(self):  # AC-20
        customer = uuid4()
        order = make_order(customer_id=customer, expected_delivery_date=date(2026, 10, 5), notes='Nota',
                           items=(('Pack', '35.00', 2), ('Chipa', '12.50', 3)))
        order.apply_discount('10.00')
        order.register_payment('25.00', 'QR', date(2026, 10, 2), 'ref-1', TODAY)
        saved = self.store(order)
        loaded = self.repository.get(order.id)
        for entity in (saved, loaded):
            self.assertEqual(entity.customer_id, customer)
            self.assertEqual(entity.sales_channel, SalesChannel.WHATSAPP)
            self.assertEqual((entity.order_date, entity.expected_delivery_date), (date(2026, 10, 1), date(2026, 10, 5)))
            self.assertEqual((entity.notes, entity.status), ('Nota', OrderStatus.NEW))
            self.assertEqual([(i.product_name, i.unit_price, i.quantity) for i in entity.items],
                             [('Pack', D('35.00'), 2), ('Chipa', D('12.50'), 3)])
            self.assertEqual((entity.subtotal, entity.discount, entity.total), (D('107.50'), D('10.00'), D('97.50')))
            self.assertEqual((entity.paid_total, entity.balance, entity.payment_status),
                             (D('25.00'), D('72.50'), PaymentStatus.PARTIAL))
            self.assertEqual([(p.amount, p.payment_method, p.payment_date, p.reference) for p in entity.payments],
                             [(D('25.00'), PaymentMethod.QR, date(2026, 10, 2), 'ref-1')])
        self.assertIsNotNone(saved.created_at)
        self.assertIsNotNone(saved.payments[0].created_at)

    def test_unknown_order_returns_none(self):
        self.assertIsNone(self.repository.get(uuid4()))
        with transaction.atomic():
            self.assertIsNone(self.repository.get_for_update(uuid4()))

    def test_state_changes_and_cancellation_are_persisted(self):  # AC-11
        order = self.store(make_order())
        order.start_preparation()
        order.cancel('Cliente desistió', NOW)
        loaded = self.store(order)
        self.assertEqual((loaded.status, loaded.cancellation_reason, loaded.cancelled_at),
                         (OrderStatus.CANCELLED, 'Cliente desistió', NOW))

    def test_delivery_date_is_persisted(self):  # AC-10
        order = self.store(make_order())
        order.start_preparation()
        order.mark_ready()
        order.deliver(date(2026, 10, 6), TODAY)
        self.assertEqual(self.store(order).delivered_date, date(2026, 10, 6))


class DerivedColumnsTests(RepositoryTestCase):
    def test_persisted_derived_values_match_the_aggregate(self):  # AC-20, INV-12
        order = make_order(items=(('Pack', '35.00', 2), ('Chipa', '12.50', 3)))
        order.apply_discount('7.50')
        order.register_payment('50.00', 'CASH', None, '', TODAY)
        self.store(order)
        row = OrderModel.objects.get(pk=order.id)
        self.assertEqual((row.subtotal, row.discount, row.total, row.paid_total, row.payment_status),
                         (order.subtotal, order.discount, order.total, order.paid_total, order.payment_status.value))
        for item in order.items:
            self.assertEqual(OrderItemModel.objects.get(pk=item.id).subtotal, item.subtotal)

    def test_derived_values_follow_every_change(self):  # AC-20
        order = self.store(make_order())
        order.change_item_quantity(order.items[0].id, 5)
        order.register_payment('175.00', 'CASH', None, '', TODAY)
        self.store(order)
        row = OrderModel.objects.get(pk=order.id)
        self.assertEqual((row.total, row.paid_total, row.payment_status), (D('175.00'), D('175.00'), 'PAID'))


class ItemAndPaymentSyncTests(RepositoryTestCase):
    def test_removed_items_are_deleted_and_others_updated(self):  # AC-05, AC-20
        order = self.store(make_order(items=(('Pack', '35.00', 2), ('Chipa', '12.50', 3))))
        first, second = order.items
        order.remove_item(second.id)
        order.change_item_quantity(first.id, 4)
        loaded = self.store(order)
        self.assertEqual([(i.id, i.quantity) for i in loaded.items], [(first.id, 4)])
        self.assertEqual(OrderItemModel.objects.filter(order_id=order.id).count(), 1)

    def test_item_order_is_preserved(self):  # AC-17
        order = self.store(make_order(items=(('A', '1.00', 1), ('B', '2.00', 1), ('C', '3.00', 1))))
        self.assertEqual([i.product_name for i in self.repository.get(order.id).items], ['A', 'B', 'C'])

    def test_a_removed_product_can_be_added_again(self):  # AC-03
        order = self.store(make_order(items=()))
        product = uuid4()
        order.add_item(product, 'A', D('1.00'), 1)
        order = self.store(order)
        order.remove_item(order.items[0].id)
        self.store(order)
        order = self.repository.get(order.id)
        order.add_item(product, 'A', D('1.00'), 2)
        self.assertEqual(self.store(order).items[0].quantity, 2)

    def test_payments_are_only_appended(self):  # AC-20, INV-10
        order = self.store(make_order())
        order.register_payment('10.00', 'CASH', None, '', TODAY)
        order = self.store(order)
        first_id = order.payments[0].id
        created_at = order.payments[0].created_at
        order.register_payment('20.00', 'QR', None, '', TODAY)
        order = self.store(order)
        self.assertEqual(len(order.payments), 2)
        self.assertEqual((order.payments[0].id, order.payments[0].created_at), (first_id, created_at))
        # Aunque el agregado en memoria perdiera un pago, guardar no borra los registrados.
        order.payments.pop(0)
        self.store(order)
        self.assertEqual(PaymentModel.objects.filter(order_id=order.id).count(), 2)


class ConstraintTests(RepositoryTestCase):
    def test_database_rejects_absurd_states(self):  # AC-20
        order = self.store(make_order())
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderModel.objects.filter(pk=order.id).update(discount=-1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderItemModel.objects.filter(order_id=order.id).update(quantity=0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PaymentModel.objects.create(order_id=order.id, amount=0, payment_method='CASH', payment_date=TODAY)

    def test_product_cannot_repeat_in_an_order(self):  # AC-03
        order = self.store(make_order())
        item = order.items[0]
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderItemModel.objects.create(order_id=order.id, product_id=item.product_id, product_name='X',
                                          unit_price=1, quantity=1, subtotal=1)


class LockingTests(RepositoryTestCase):
    def test_get_for_update_returns_the_aggregate_inside_a_transaction(self):  # AC-20
        order = self.store(make_order())
        with transaction.atomic():
            self.assertEqual(self.repository.get_for_update(order.id).id, order.id)

    def test_get_for_update_locks_the_row(self):  # AC-20
        order = self.store(make_order())
        with transaction.atomic():
            self.repository.get_for_update(order.id)
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1 FROM pg_locks WHERE pid = pg_backend_pid() AND mode = %s', ['RowShareLock'])
                self.assertTrue(cursor.fetchall())


class LockingOutsideTransactionTests(TransactionTestCase):
    def test_get_for_update_fails_without_an_open_transaction(self):  # AC-20
        # Por eso las vistas de Sales abren `transaction.atomic()` antes de cada mutación.
        repository = DjangoOrderRepository()
        order = repository.save(make_order())
        with self.assertRaises(TransactionManagementError):
            repository.get_for_update(order.id)


class ListTests(RepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.customer = uuid4()
        self.pending = self.store(make_order(date(2026, 10, 1), 'WHATSAPP', customer_id=self.customer,
                                             expected_delivery_date=date(2026, 10, 12)))
        self.paid = self.store(make_order(date(2026, 10, 3), 'STORE', expected_delivery_date=date(2026, 10, 9)))
        self.paid.register_payment('70.00', 'CASH', None, '', TODAY)
        self.paid = self.store(self.paid)
        self.partial = self.store(make_order(date(2026, 10, 5), 'FAIR'))
        self.partial.register_payment('10.00', 'QR', None, '', TODAY)
        self.partial = self.store(self.partial)
        self.cancelled = self.store(make_order(date(2026, 10, 7), 'FACEBOOK', expected_delivery_date=date(2026, 10, 8)))
        self.cancelled.cancel('No', NOW)
        self.cancelled = self.store(self.cancelled)

    def ids(self, **filters):
        return [o.id for o in self.repository.list(OrderFilters(**filters))]

    def test_default_order_is_newest_first(self):  # AC-16
        self.assertEqual(self.ids(), [self.cancelled.id, self.partial.id, self.paid.id, self.pending.id])
        self.assertEqual(self.ids(ordering=NEWEST_FIRST), self.ids())

    def test_order_by_expected_delivery_puts_missing_dates_last(self):  # AC-16
        self.assertEqual(self.ids(ordering=BY_EXPECTED_DELIVERY),
                         [self.cancelled.id, self.paid.id, self.pending.id, self.partial.id])

    def test_filters_by_status_and_payment_status(self):  # AC-16
        self.assertEqual(self.ids(statuses=(OrderStatus.CANCELLED,)), [self.cancelled.id])
        self.assertEqual(set(self.ids(statuses=(OrderStatus.NEW, OrderStatus.CANCELLED))),
                         {self.pending.id, self.paid.id, self.partial.id, self.cancelled.id})
        self.assertEqual(self.ids(payment_statuses=(PaymentStatus.PAID,)), [self.paid.id])
        self.assertEqual(set(self.ids(payment_statuses=(PaymentStatus.PENDING, PaymentStatus.PARTIAL))),
                         {self.pending.id, self.partial.id, self.cancelled.id})

    def test_filters_by_channel_and_customer(self):  # AC-08, AC-16
        self.assertEqual(self.ids(sales_channel=SalesChannel.STORE), [self.paid.id])
        self.assertEqual(self.ids(customer_id=self.customer), [self.pending.id])
        self.assertEqual(self.ids(customer_id=uuid4()), [])  # EDGE-09

    def test_filters_by_date_range_on_either_field(self):  # AC-10, AC-16
        self.assertEqual(self.ids(date_from=date(2026, 10, 3), date_to=date(2026, 10, 5)), [self.partial.id, self.paid.id])
        self.assertEqual(
            self.ids(date_field='expected_delivery_date', date_from=date(2026, 10, 9), date_to=date(2026, 10, 12),
                     ordering=BY_EXPECTED_DELIVERY),
            [self.paid.id, self.pending.id])
        self.assertEqual(self.ids(date_field='expected_delivery_date', date_from=date(2026, 10, 13)), [])

    def test_has_balance_selects_what_is_still_owed(self):  # AC-16
        self.assertEqual(set(self.ids(has_balance=True)), {self.pending.id, self.partial.id, self.cancelled.id})
        self.assertEqual(self.ids(has_balance=False), [self.paid.id])

    def test_combined_filters_for_receivable_orders(self):  # AC-16
        receivable = self.ids(has_balance=True, statuses=(OrderStatus.NEW, OrderStatus.IN_PREPARATION,
                                                          OrderStatus.READY, OrderStatus.DELIVERED))
        self.assertEqual(set(receivable), {self.pending.id, self.partial.id})

    def test_summaries_use_persisted_amounts_without_loading_children(self):  # AC-16
        with self.assertNumQueries(1):
            rows = list(self.repository.list(OrderFilters()))
        by_id = {r.id: r for r in rows}
        summary = by_id[self.partial.id]
        self.assertEqual((summary.total, summary.paid_total, summary.balance, summary.payment_status),
                         (D('70.00'), D('10.00'), D('60.00'), PaymentStatus.PARTIAL))

    def test_lazy_list_supports_count_and_slicing(self):  # AC-16
        result = self.repository.list(OrderFilters())
        self.assertEqual(len(result), 4)
        self.assertEqual([r.id for r in result[1:3]], [self.partial.id, self.paid.id])


class QueryCountTests(RepositoryTestCase):
    def test_loading_an_order_uses_a_fixed_number_of_queries(self):  # NFR rendimiento
        order = self.store(make_order(items=(('A', '1.00', 1), ('B', '2.00', 1), ('C', '3.00', 1))))
        with self.assertNumQueries(3):
            self.repository.get(order.id)
        self.assertEqual(OrderModel.objects.filter(total__gt=F('paid_total')).count(), 1)
