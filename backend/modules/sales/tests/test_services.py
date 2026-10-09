"""Fachada de solo lectura de Sales: se prueba con pedidos reales creados por el agregado y su repositorio."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

from modules.sales import services
from modules.sales.domain.order import Order
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository

D = Decimal
TODAY = date(2026, 10, 20)
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
START, END = date(2026, 10, 1), date(2026, 10, 31)


class SalesServicesTestCase(TestCase):
    def setUp(self):
        self.repository = DjangoOrderRepository()

    def order(self, on=date(2026, 10, 5), channel='WHATSAPP', items=(('Pack', '35.00', 2),), customer_id=None,
              discount=None, paid=None, expected=None, status=None, product_ids=None) -> Order:
        order = Order.create(sales_channel=channel, order_date=on, customer_id=customer_id,
                             expected_delivery_date=expected)
        for index, (name, price, quantity) in enumerate(items):
            product_id = product_ids[index] if product_ids else uuid4()
            order.add_item(product_id, name, D(price), quantity)
        if discount:
            order.apply_discount(discount)
        if paid:
            order.register_payment(paid, 'CASH', on, '', TODAY)
        if status == 'IN_PREPARATION':
            order.start_preparation()
        elif status == 'READY':
            order.start_preparation()
            order.mark_ready()
        elif status == 'DELIVERED':
            order.start_preparation()
            order.mark_ready()
            order.deliver(on, TODAY)
        elif status == 'CANCELLED':
            order.cancel('Motivo', NOW)
        return self.repository.save(order)


class SalesTotalsTests(SalesServicesTestCase):
    def test_sums_totals_net_of_discount_for_valid_orders(self):  # AC-10, INV-08
        self.order(items=(('Pack', '35.00', 2),))                       # 70.00
        self.order(items=(('Chipa', '10.00', 3),), discount='5.00')    # 25.00
        totals = services.get_sales_totals(START, END)
        self.assertEqual((totals.total, totals.orders_count), (D('95.00'), 2))

    def test_cancelled_orders_and_orders_without_items_do_not_count(self):  # AC-10, EDGE-05, EDGE-06
        self.order()
        self.order(status='CANCELLED', paid='10.00')
        self.repository.save(Order.create(sales_channel='WHATSAPP', order_date=date(2026, 10, 6)))  # sin ítems
        totals = services.get_sales_totals(START, END)
        self.assertEqual((totals.total, totals.orders_count), (D('70.00'), 1))

    def test_zero_priced_order_with_items_is_valid(self):  # EDGE-05
        self.order(items=(('Muestra', '0.00', 1),))
        totals = services.get_sales_totals(START, END)
        self.assertEqual((totals.total, totals.orders_count), (D('0.00'), 1))

    def test_payments_do_not_change_sales(self):  # AC-10
        self.order(paid='70.00')
        self.order(on=date(2026, 10, 6))
        self.assertEqual(services.get_sales_totals(START, END).total, D('140.00'))

    def test_range_is_inclusive_by_order_date(self):  # EDGE-02
        self.order(on=date(2026, 10, 1))
        self.order(on=date(2026, 10, 31))
        self.order(on=date(2026, 9, 30))
        self.order(on=date(2026, 11, 1))
        self.assertEqual(services.get_sales_totals(START, END).orders_count, 2)
        self.assertEqual(services.get_sales_totals(date(2026, 10, 31), date(2026, 10, 31)).orders_count, 1)

    def test_empty_range_is_zero(self):  # EDGE-03
        totals = services.get_sales_totals(START, END)
        self.assertEqual((totals.total, totals.orders_count), (D('0.00'), 0))


class SalesByChannelTests(SalesServicesTestCase):
    def test_groups_valid_orders_by_channel_highest_first(self):  # AC-15
        self.order(channel='WHATSAPP', items=(('A', '10.00', 1),))
        self.order(channel='WHATSAPP', items=(('A', '10.00', 1),))
        self.order(channel='STORE', items=(('A', '100.00', 1),))
        self.order(channel='FAIR', status='CANCELLED')
        rows = services.get_sales_by_channel(START, END)
        self.assertEqual([(r.sales_channel, r.orders_count, r.total) for r in rows],
                         [('STORE', 1, D('100.00')), ('WHATSAPP', 2, D('20.00'))])


class TopProductsTests(SalesServicesTestCase):
    def test_groups_by_product_with_units_and_amount_before_discount(self):  # AC-16
        a, b = uuid4(), uuid4()
        self.order(items=(('Pack', '35.00', 2), ('Chipa', '10.00', 5)), product_ids=[a, b], discount='20.00')
        self.order(items=(('Pack', '35.00', 1),), product_ids=[a])
        products = services.get_top_products(START, END)
        self.assertEqual([(p.product_id, p.units, p.amount) for p in products],
                         [(b, 5, D('50.00')), (a, 3, D('105.00'))])

    def test_uses_the_most_recent_snapshot_name(self):  # EDGE-14
        a = uuid4()
        self.order(on=date(2026, 10, 2), items=(('Pack viejo', '35.00', 1),), product_ids=[a])
        self.order(on=date(2026, 10, 9), items=(('Pack nuevo', '40.00', 1),), product_ids=[a])
        products = services.get_top_products(START, END)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].product_name, 'Pack nuevo')

    def test_ties_are_ordered_by_amount_then_name(self):  # EDGE-12
        self.order(items=(('Beta', '10.00', 2), ('Alfa', '10.00', 2), ('Mayor', '30.00', 2)))
        names = [p.product_name for p in services.get_top_products(START, END)]
        self.assertEqual(names, ['Mayor', 'Alfa', 'Beta'])

    def test_excludes_cancelled_and_out_of_range_orders_and_applies_limit(self):  # AC-16
        self.order(items=(('Cancelado', '10.00', 9),), status='CANCELLED')
        self.order(on=date(2026, 9, 1), items=(('Fuera', '10.00', 9),))
        for index in range(12):
            self.order(items=((f'P{index:02d}', '1.00', 1),))
        products = services.get_top_products(START, END, limit=10)
        self.assertEqual(len(products), 10)
        self.assertNotIn('Cancelado', [p.product_name for p in products])
        self.assertNotIn('Fuera', [p.product_name for p in products])


class TopCustomersTests(SalesServicesTestCase):
    def test_ranks_customers_by_total_then_orders_and_skips_orders_without_customer(self):  # AC-17
        ana, luis, eva = uuid4(), uuid4(), uuid4()
        self.order(customer_id=ana, items=(('A', '50.00', 1),))
        self.order(customer_id=ana, items=(('A', '50.00', 1),))
        self.order(customer_id=luis, items=(('A', '100.00', 1),))
        self.order(customer_id=eva, items=(('A', '10.00', 1),), status='CANCELLED')
        self.order(customer_id=None, items=(('A', '999.00', 1),))
        rows = services.get_top_customers(START, END)
        self.assertEqual([(r.customer_id, r.orders_count, r.total) for r in rows],
                         [(ana, 2, D('100.00')), (luis, 1, D('100.00'))])

    def test_limit(self):
        for _ in range(3):
            self.order(customer_id=uuid4())
        self.assertEqual(len(services.get_top_customers(START, END, limit=2)), 2)


class PendingTests(SalesServicesTestCase):
    def test_delivered_and_partially_paid_is_only_pending_collection(self):  # AC-18, EDGE-07
        order = self.order(status='DELIVERED', paid='20.00')
        delivery = services.get_pending_delivery()
        collection = services.get_pending_collection()
        self.assertEqual(delivery.count, 0)
        self.assertEqual([r.id for r in collection.rows], [order.id])
        self.assertEqual((collection.count, collection.balance_total), (1, D('50.00')))
        self.assertEqual(collection.rows[0].balance, D('50.00'))

    def test_ready_and_paid_is_only_pending_delivery(self):  # EDGE-07
        order = self.order(status='READY', paid='70.00')
        self.assertEqual([r.id for r in services.get_pending_delivery().rows], [order.id])
        self.assertEqual(services.get_pending_collection().count, 0)

    def test_delivered_and_paid_is_in_neither(self):  # EDGE-07
        self.order(status='DELIVERED', paid='70.00')
        self.assertEqual((services.get_pending_delivery().count, services.get_pending_collection().count), (0, 0))

    def test_cancelled_orders_are_never_pending(self):  # EDGE-06
        self.order(status='CANCELLED', paid='10.00')
        self.assertEqual((services.get_pending_delivery().count, services.get_pending_collection().count), (0, 0))

    def test_pending_does_not_depend_on_any_period(self):  # AC-18, INV-10
        self.order(on=date(2020, 1, 1))
        self.assertEqual(services.get_pending_delivery().count, 1)
        self.assertEqual(services.get_pending_collection().count, 1)

    def test_orders_without_items_are_not_pending(self):  # EDGE-05
        self.repository.save(Order.create(sales_channel='WHATSAPP', order_date=date(2026, 10, 6)))
        self.assertEqual((services.get_pending_delivery().count, services.get_pending_collection().count), (0, 0))

    def test_delivery_is_sorted_by_expected_date_with_nulls_last(self):  # AC-18
        late = self.order(expected=date(2026, 10, 20))
        none = self.order(on=date(2026, 10, 1))
        soon = self.order(expected=date(2026, 10, 8))
        rows = services.get_pending_delivery().rows
        self.assertEqual([r.id for r in rows], [soon.id, late.id, none.id])

    def test_collection_is_sorted_oldest_first_and_limited(self):  # AC-18
        orders = [self.order(on=date(2026, 10, day)) for day in (9, 3, 6)]
        rows = services.get_pending_collection(limit=2).rows
        self.assertEqual([r.id for r in rows], [orders[1].id, orders[2].id])
        self.assertEqual(services.get_pending_collection(limit=2).count, 3)

    def test_fully_paid_orders_have_no_balance(self):
        self.order(paid='70.00')
        self.assertEqual(services.get_pending_collection().count, 0)
