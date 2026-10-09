"""Adaptadores de los puertos de Reporting sobre las fachadas públicas de otros módulos y el reloj de Django.

Es el único lugar de Reporting que conoce a Sales, Expenses y Customers, y solo por sus `services.py`.
"""
from collections.abc import Iterable, Sequence
from datetime import date
from uuid import UUID

from django.utils import timezone

from modules.customers import services as customer_services
from modules.expenses import services as expense_services
from modules.reporting.application import ports
from modules.sales import services as sales_services


def _pending(pending: sales_services.PendingOrders) -> ports.PendingOrders:
    rows = [
        ports.PendingOrder(id=o.id, customer_id=o.customer_id, order_date=o.order_date,
                           expected_delivery_date=o.expected_delivery_date, status=o.status,
                           payment_status=o.payment_status, total=o.total, balance=o.balance)
        for o in pending.rows
    ]
    return ports.PendingOrders(count=pending.count, balance_total=pending.balance_total, rows=rows)


class SalesReaderAdapter:
    def totals(self, date_from: date, date_to: date) -> ports.SalesTotals:
        totals = sales_services.get_sales_totals(date_from, date_to)
        return ports.SalesTotals(total=totals.total, orders_count=totals.orders_count)

    def by_channel(self, date_from: date, date_to: date) -> Sequence[ports.ChannelSales]:
        return [ports.ChannelSales(sales_channel=c.sales_channel, orders_count=c.orders_count, total=c.total)
                for c in sales_services.get_sales_by_channel(date_from, date_to)]

    def top_products(self, date_from: date, date_to: date, limit: int) -> Sequence[ports.ProductSales]:
        return [ports.ProductSales(product_id=p.product_id, product_name=p.product_name, units=p.units,
                                   amount=p.amount)
                for p in sales_services.get_top_products(date_from, date_to, limit)]

    def top_customers(self, date_from: date, date_to: date, limit: int) -> Sequence[ports.CustomerSales]:
        return [ports.CustomerSales(customer_id=c.customer_id, orders_count=c.orders_count, total=c.total)
                for c in sales_services.get_top_customers(date_from, date_to, limit)]

    def pending_delivery(self, limit: int) -> ports.PendingOrders:
        return _pending(sales_services.get_pending_delivery(limit))

    def pending_collection(self, limit: int) -> ports.PendingOrders:
        return _pending(sales_services.get_pending_collection(limit))


class ExpensesReaderAdapter:
    def report(self, date_from: date, date_to: date) -> ports.ExpenseTotals:
        report = expense_services.get_expense_report(date_from, date_to)
        categories = [ports.CategoryExpense(category_id=r.category_id, name=r.name, active=r.active, total=r.total)
                      for r in report.rows]
        return ports.ExpenseTotals(total=report.total, categories=categories)


class CustomerNamesAdapter:
    def get_customer_names(self, customer_ids: Iterable[UUID]) -> dict[UUID, str]:
        return customer_services.get_customer_names(customer_ids)


class SystemClock:
    """"Hoy" según la zona horaria configurada (`TIME_ZONE`), no la del navegador."""

    def today(self) -> date:
        return timezone.localdate()
