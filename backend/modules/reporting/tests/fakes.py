"""Dobles en memoria de los puertos de Reporting, para probar casos de uso sin base de datos."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from modules.reporting.application.ports import (
    CategoryExpense,
    ChannelSales,
    CustomerSales,
    ExpenseTotals,
    PendingOrder,
    PendingOrders,
    ProductSales,
    SalesTotals,
)

TODAY = date(2026, 10, 14)
D = Decimal


class FakeClock:
    def today(self):
        return TODAY


class FakeSales:
    def __init__(self, total='0.00', orders=0):
        self.total, self.orders = D(total), orders
        self.calls = []
        self.channels, self.products, self.customers = [], [], []
        self.delivery = PendingOrders(count=0, balance_total=D('0.00'), rows=[])
        self.collection = PendingOrders(count=0, balance_total=D('0.00'), rows=[])

    def totals(self, date_from, date_to):
        self.calls.append(('totals', date_from, date_to))
        return SalesTotals(total=self.total, orders_count=self.orders)

    def by_channel(self, date_from, date_to):
        return list(self.channels)

    def top_products(self, date_from, date_to, limit):
        self.calls.append(('top_products', limit))
        return list(self.products)

    def top_customers(self, date_from, date_to, limit):
        self.calls.append(('top_customers', limit))
        return list(self.customers)

    def pending_delivery(self, limit):
        self.calls.append(('pending_delivery', limit))
        return self.delivery

    def pending_collection(self, limit):
        self.calls.append(('pending_collection', limit))
        return self.collection


class FakeExpenses:
    def __init__(self, total='0.00', categories=()):
        self.total, self.categories = D(total), tuple(categories)
        self.calls = []

    def report(self, date_from, date_to):
        self.calls.append((date_from, date_to))
        return ExpenseTotals(total=self.total, categories=self.categories)


class FakeCustomers:
    def __init__(self, names=None):
        self.names = names or {}

    def get_customer_names(self, ids):
        return {i: self.names[i] for i in ids if i in self.names}


def pending_order(customer_id=None, total='100.00', balance='40.00', status='DELIVERED') -> PendingOrder:
    return PendingOrder(id=uuid4(), customer_id=customer_id, order_date=date(2026, 10, 1),
                        expected_delivery_date=None, status=status, payment_status='PARTIAL',
                        total=D(total), balance=D(balance))


__all__ = ['FakeClock', 'FakeSales', 'FakeExpenses', 'FakeCustomers', 'pending_order', 'TODAY', 'D',
           'CategoryExpense', 'ChannelSales', 'CustomerSales', 'ProductSales', 'PendingOrders']
