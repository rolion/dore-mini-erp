from datetime import date
from uuid import uuid4

from django.test import SimpleTestCase

from modules.reporting.application import queries
from modules.reporting.application.criteria import SALES_CRITERIA
from modules.reporting.application.queries import PeriodParams
from modules.reporting.domain.period import PeriodError, PeriodKind

from .fakes import (
    D,
    TODAY,
    CategoryExpense,
    ChannelSales,
    CustomerSales,
    FakeClock,
    FakeCustomers,
    FakeExpenses,
    FakeSales,
    PendingOrders,
    ProductSales,
    pending_order,
)

MONTH = PeriodParams(kind='month')


class AverageTicketTests(SimpleTestCase):
    def test_divides_total_by_orders_and_rounds_to_cents(self):  # AC-13
        self.assertEqual(queries.average_ticket(D('100.00'), 3), D('33.33'))
        self.assertEqual(queries.average_ticket(D('10.00'), 4), D('2.50'))

    def test_no_orders_means_no_average(self):  # AC-13, EDGE-03
        self.assertIsNone(queries.average_ticket(D('0.00'), 0))
        self.assertIsNone(queries.average_ticket(D('50.00'), 0))


class DashboardSummaryTests(SimpleTestCase):
    def summary(self, sales, expenses, params=MONTH):
        return queries.GetDashboardSummary(sales, expenses, FakeClock()).execute(params)

    def test_profit_is_sales_minus_expenses(self):  # AC-12, INV-09
        summary = self.summary(FakeSales('1200.00', 4), FakeExpenses('450.00'))
        self.assertEqual((summary.sales_total, summary.expenses_total), (D('1200.00'), D('450.00')))
        self.assertEqual(summary.estimated_profit, D('750.00'))
        self.assertEqual(summary.average_ticket, D('300.00'))
        self.assertEqual(summary.sales_criteria, SALES_CRITERIA)

    def test_profit_can_be_negative(self):  # AC-12, EDGE-04
        summary = self.summary(FakeSales('100.00', 1), FakeExpenses('250.50'))
        self.assertEqual(summary.estimated_profit, D('-150.50'))

    def test_empty_period_is_zero_with_no_average(self):  # AC-13, EDGE-03
        summary = self.summary(FakeSales(), FakeExpenses())
        self.assertEqual((summary.sales_total, summary.expenses_total, summary.estimated_profit),
                         (D('0.00'), D('0.00'), D('0.00')))
        self.assertEqual((summary.orders_count, summary.average_ticket), (0, None))

    def test_pending_counts_come_from_sales_regardless_of_the_period(self):  # INV-10
        sales = FakeSales('10.00', 1)
        sales.delivery = PendingOrders(count=3, balance_total=D('0.00'), rows=[])
        sales.collection = PendingOrders(count=2, balance_total=D('85.50'), rows=[])
        for params in (MONTH, PeriodParams(kind='day'), PeriodParams(date_from=date(2020, 1, 1),
                                                                        date_to=date(2020, 1, 2))):
            summary = self.summary(sales, FakeExpenses(), params)
            self.assertEqual((summary.pending_delivery_count, summary.pending_collection_count,
                              summary.pending_collection_balance), (3, 2, D('85.50')))

    def test_uses_the_resolved_period_for_both_sources(self):  # AC-14
        sales, expenses = FakeSales(), FakeExpenses()
        summary = self.summary(sales, expenses, PeriodParams(kind='week'))
        self.assertEqual(summary.period.kind, PeriodKind.WEEK)
        window = (date(2026, 10, 12), date(2026, 10, 18))
        self.assertEqual(sales.calls[0][1:], window)
        self.assertEqual(expenses.calls[0], window)

    def test_invalid_period_raises(self):  # AC-14
        with self.assertRaises(PeriodError):
            self.summary(FakeSales(), FakeExpenses(), PeriodParams(kind='year'))


class ReportsTests(SimpleTestCase):
    def test_sales_report(self):  # AC-10
        report = queries.GetSalesReport(FakeSales('90.00', 3), FakeClock()).execute(MONTH)
        self.assertEqual((report.total, report.orders_count, report.average_ticket, report.criteria),
                         (D('90.00'), 3, D('30.00'), SALES_CRITERIA))

    def test_expense_report_keeps_the_categories_and_total(self):  # AC-11
        categories = [CategoryExpense(uuid4(), 'Materia prima', True, D('70.00')),
                      CategoryExpense(uuid4(), 'Empaque', False, D('30.00'))]
        report = queries.GetExpenseReport(FakeExpenses('100.00', categories), FakeClock()).execute(MONTH)
        self.assertEqual(report.total, sum(c.total for c in report.categories))
        self.assertEqual([c.name for c in report.categories], ['Materia prima', 'Empaque'])

    def test_sales_by_channel(self):  # AC-15
        sales = FakeSales()
        sales.channels = [ChannelSales('STORE', 1, D('10.00'))]
        report = queries.GetSalesByChannel(sales, FakeClock()).execute(MONTH)
        self.assertEqual([c.sales_channel for c in report.channels], ['STORE'])

    def test_top_products_passes_the_limit(self):  # AC-16
        sales = FakeSales()
        sales.products = [ProductSales(uuid4(), 'Pack', 5, D('50.00'))]
        report = queries.GetTopProducts(sales, FakeClock()).execute(MONTH)
        self.assertEqual((report.limit, [p.product_name for p in report.products]), (10, ['Pack']))
        self.assertIn(('top_products', 10), sales.calls)

    def test_top_customers_resolves_names_and_tolerates_missing_ones(self):  # AC-17, EDGE-13
        ana, ghost = uuid4(), uuid4()
        sales = FakeSales()
        sales.customers = [CustomerSales(ana, 2, D('100.00')), CustomerSales(ghost, 1, D('50.00'))]
        report = queries.GetTopCustomers(sales, FakeCustomers({ana: 'Ana'}), FakeClock()).execute(MONTH)
        self.assertEqual([(c.name, c.orders_count, c.total) for c in report.customers],
                         [('Ana', 2, D('100.00')), ('', 1, D('50.00'))])


class PendingOrdersTests(SimpleTestCase):
    def test_builds_both_lists_with_customer_names(self):  # AC-18
        ana = uuid4()
        sales = FakeSales()
        with_customer, without = pending_order(customer_id=ana), pending_order()
        sales.delivery = PendingOrders(count=1, balance_total=D('0.00'), rows=[without])
        sales.collection = PendingOrders(count=5, balance_total=D('200.00'), rows=[with_customer])
        report = queries.GetPendingOrders(sales, FakeCustomers({ana: 'Ana'})).execute()
        self.assertEqual((report.delivery.count, report.collection.count, report.collection.balance_total),
                         (1, 5, D('200.00')))
        self.assertEqual(report.collection.rows[0].customer_name, 'Ana')
        self.assertEqual(report.delivery.rows[0].customer_name, '')
        self.assertIn(('pending_delivery', 10), sales.calls)
