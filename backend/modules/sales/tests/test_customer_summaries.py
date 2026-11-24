"""Fachada de Ventas para CRM: pedidos válidos, última compra y saldo por cliente (AC-05, INV-02)."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

from modules.sales import services
from modules.sales.domain.order import Order
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository

D = Decimal
TODAY = date(2026, 11, 20)
NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


class CustomerSummariesTests(TestCase):
    def setUp(self):
        self.company_id = uuid4()
        self.repository = DjangoOrderRepository(self.company_id)
        self.ana, self.beto = uuid4(), uuid4()

    def order(self, customer_id, total='50.00', paid=None, on=date(2026, 11, 1), items=True, cancel=False,
              warehouse_id=None, repository=None):
        order = Order.create(sales_channel='WHATSAPP', order_date=on, customer_id=customer_id)
        if items:
            order.add_item(uuid4(), 'Pack', D(total), 1)
        if paid:
            order.register_payment(D(paid), 'CASH', on, '', TODAY)
        if warehouse_id:
            order.assign_warehouse(warehouse_id)
        if cancel:
            order.cancel('Motivo', NOW)
        return (repository or self.repository).save(order)

    def summaries(self, *ids, company_id=None):
        return services.get_customer_commercial_summaries(company_id or self.company_id, ids)

    def test_counts_last_date_and_balance_only_for_valid_orders(self):
        self.order(self.ana, total='50.00', paid='20.00', on=date(2026, 11, 1))   # saldo 30.00
        self.order(self.ana, total='40.00', paid='40.00', on=date(2026, 11, 10))  # saldado: no suma saldo
        self.order(self.ana, total='99.00', on=date(2026, 11, 15), cancel=True)   # cancelado: no cuenta
        self.order(self.ana, on=date(2026, 11, 18), items=False)                  # sin ítems: no cuenta
        summary = self.summaries(self.ana)[self.ana]
        self.assertEqual((summary.order_count, summary.last_purchase_date, summary.outstanding_amount),
                         (2, date(2026, 11, 10), D('30.00')))

    def test_customers_without_valid_orders_are_absent(self):
        self.order(self.beto, cancel=True)
        self.assertEqual(self.summaries(self.ana, self.beto), {})
        self.assertEqual(self.summaries(), {})

    def test_summaries_are_per_customer_and_per_company(self):
        other = DjangoOrderRepository(uuid4())
        self.order(self.ana, total='10.00')
        self.order(self.beto, total='20.00')
        self.order(self.ana, total='999.00', repository=other)
        found = self.summaries(self.ana, self.beto)
        self.assertEqual((found[self.ana].outstanding_amount, found[self.beto].outstanding_amount),
                         (D('10.00'), D('20.00')))
        self.assertEqual(self.summaries(self.ana, company_id=other.company_id)[self.ana].outstanding_amount,
                         D('999.00'))

    def test_a_single_aggregate_query_serves_any_number_of_customers(self):
        customers = [uuid4() for _ in range(6)]
        for customer in customers:
            self.order(customer)
        with self.assertNumQueries(1):
            found = self.summaries(*customers)
        self.assertEqual(len(found), 6)

    def test_customers_in_warehouse_only_valid_orders_of_the_company(self):
        warehouse = uuid4()
        self.order(self.ana, warehouse_id=warehouse)
        self.order(self.beto, warehouse_id=warehouse, cancel=True)
        self.order(uuid4(), warehouse_id=warehouse, repository=DjangoOrderRepository(uuid4()))
        self.order(uuid4())  # sin almacén
        self.assertEqual(services.list_customer_ids_with_orders_in_warehouse(self.company_id, warehouse), [self.ana])
