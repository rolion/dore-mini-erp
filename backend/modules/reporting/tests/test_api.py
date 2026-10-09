"""API de Reporting contra PostgreSQL, con pedidos creados por el agregado de Sales y gastos por Expenses."""
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from modules.customers.infrastructure.django.models import CustomerModel
from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.domain.expense import Expense
from modules.expenses.infrastructure.django.repositories import (
    DjangoExpenseCategoryRepository,
    DjangoExpenseRepository,
)
from modules.reporting.application.criteria import SALES_CRITERIA
from modules.sales.domain.order import Order
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository

D = Decimal
WEDNESDAY = date(2026, 10, 14)
NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
BASE = '/api/reports/'
PERIOD_ROUTES = ('dashboard', 'sales', 'expenses', 'sales-by-channel', 'top-products', 'top-customers')


class ReportingApiTestCase(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='ana', password='x-Pass-123')
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        patcher = mock.patch('modules.reporting.infrastructure.adapters.timezone.localdate', return_value=WEDNESDAY)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.orders = DjangoOrderRepository()
        self.categories = DjangoExpenseCategoryRepository()
        self.expenses = DjangoExpenseRepository()

    # --- fixtures ---
    def order(self, on=date(2026, 10, 5), channel='WHATSAPP', items=(('Pack', '35.00', 2),), customer_id=None,
              discount=None, paid=None, expected=None, status=None):
        order = Order.create(sales_channel=channel, order_date=on, customer_id=customer_id,
                             expected_delivery_date=expected)
        for name, price, quantity in items:
            order.add_item(uuid4(), name, D(price), quantity)
        if discount:
            order.apply_discount(discount)
        if paid:
            order.register_payment(paid, 'CASH', on, '', WEDNESDAY)
        if status in ('IN_PREPARATION', 'READY', 'DELIVERED'):
            order.start_preparation()
        if status in ('READY', 'DELIVERED'):
            order.mark_ready()
        if status == 'DELIVERED':
            order.deliver(on, WEDNESDAY)
        if status == 'CANCELLED':
            order.cancel('Motivo', NOW)
        return self.orders.save(order)

    def category(self, name='Materia prima', active=True):
        category = ExpenseCategory.create(name)
        category.active = active
        return self.categories.save(category)

    def expense(self, category, amount, on=date(2026, 10, 5), voided=False):
        expense = self.expenses.save(Expense.create('Gasto', amount, category.id, on))
        if voided:
            expense.void(NOW)
            self.expenses.save(expense)
        return expense

    def get(self, route, **params):
        response = self.client.get(f'{BASE}{route}/', params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()


class AuthenticationTests(APITestCase):
    def test_every_route_requires_authentication(self):  # AC-19
        for route in (*PERIOD_ROUTES, 'pending'):
            with self.subTest(route=route):
                self.assertEqual(APIClient().get(f'{BASE}{route}/').status_code, 401)

    def test_routes_are_read_only(self):  # Reporting solo lee
        user = get_user_model().objects.create_user(username='luis', password='x-Pass-123')
        client = APIClient()
        client.force_authenticate(user)
        for route in (*PERIOD_ROUTES, 'pending'):
            with self.subTest(route=route):
                self.assertEqual(client.post(f'{BASE}{route}/', {}, format='json').status_code, 405)


class PeriodParametersTests(ReportingApiTestCase):
    def test_every_period_route_reports_the_effective_period(self):  # AC-14
        expected = {'kind': 'month', 'date_from': '2026-10-01', 'date_to': '2026-10-31'}
        for route in PERIOD_ROUTES:
            with self.subTest(route=route):
                self.assertEqual(self.get(route)['period'], expected)

    def test_named_periods_and_ranges(self):  # AC-14
        self.assertEqual(self.get('sales', period='day')['period'],
                         {'kind': 'day', 'date_from': '2026-10-14', 'date_to': '2026-10-14'})
        self.assertEqual(self.get('sales', period='week')['period'],
                         {'kind': 'week', 'date_from': '2026-10-12', 'date_to': '2026-10-18'})
        self.assertEqual(self.get('sales', date_from='2026-01-01', date_to='2026-03-31')['period'],
                         {'kind': 'range', 'date_from': '2026-01-01', 'date_to': '2026-03-31'})

    def test_invalid_combinations_are_400_per_parameter(self):  # AC-14
        for params, field in (
            ({'period': 'year'}, 'period'),
            ({'period': 'week', 'date_from': '2026-01-01', 'date_to': '2026-01-02'}, 'period'),
            ({'date_from': '2026-01-01'}, 'date_to'),
            ({'date_to': '2026-01-01'}, 'date_from'),
            ({'date_from': '2026-02-01', 'date_to': '2026-01-01'}, 'date_to'),
            ({'date_from': 'ayer', 'date_to': '2026-01-01'}, 'date_from'),
        ):
            for route in ('dashboard', 'expenses'):
                with self.subTest(params=params, route=route):
                    response = self.client.get(f'{BASE}{route}/', params)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(list(response.json()), [field])


class SalesReportApiTests(ReportingApiTestCase):
    def test_total_orders_and_average_ticket_of_valid_orders(self):  # AC-10, AC-13
        self.order(items=(('Pack', '35.00', 2),))                      # 70
        self.order(items=(('Chipa', '10.00', 3),), discount='5.00')   # 25
        self.order(status='CANCELLED', paid='10.00')
        self.order(on=date(2026, 9, 20))
        report = self.get('sales')
        self.assertEqual((report['total'], report['orders_count'], report['average_ticket']), ('95.00', 2, '47.50'))
        self.assertEqual(report['criteria'], SALES_CRITERIA)

    def test_payments_do_not_change_sales(self):  # AC-10
        self.order(paid='70.00')
        self.assertEqual(self.get('sales')['total'], '70.00')

    def test_no_orders_is_zero_with_null_average(self):  # AC-13, EDGE-03
        report = self.get('sales')
        self.assertEqual((report['total'], report['orders_count'], report['average_ticket']), ('0.00', 0, None))


class ExpensesReportApiTests(ReportingApiTestCase):
    def test_groups_by_category_excluding_voided_and_totals_match(self):  # AC-11
        raw, packing = self.category('Materia prima'), self.category('Empaque', active=False)
        self.expense(raw, '100.00')
        self.expense(raw, '50.50')
        self.expense(packing, '20.00')
        self.expense(raw, '999.00', voided=True)
        self.expense(raw, '7.00', on=date(2026, 9, 1))
        report = self.get('expenses')
        self.assertEqual(report['total'], '170.50')
        self.assertEqual([(c['name'], c['active'], c['total']) for c in report['categories']],
                         [('Materia prima', True, '150.50'), ('Empaque', False, '20.00')])
        self.assertEqual(sum(D(c['total']) for c in report['categories']), D(report['total']))

    def test_editing_an_expense_changes_later_reports(self):  # AC-06
        category = self.category()
        expense = self.expense(category, '10.00')
        expense.update(amount='25.00')
        self.expenses.save(expense)
        self.assertEqual(self.get('expenses')['total'], '25.00')

    def test_voiding_removes_it_from_the_total(self):  # AC-07
        category = self.category()
        expense = self.expense(category, '10.00')
        expense.void(NOW)
        self.expenses.save(expense)
        self.assertEqual(self.get('expenses')['total'], '0.00')


class DashboardApiTests(ReportingApiTestCase):
    def test_summary_with_profit_and_pending_counts(self):  # AC-12, AC-18
        self.order(items=(('Pack', '100.00', 1),), paid='30.00', status='READY')          # saldo 70, entrega
        self.order(items=(('Pack', '50.00', 1),), status='DELIVERED', paid='20.00')        # saldo 30, solo cobro
        self.expense(self.category(), '40.00')
        data = self.get('dashboard')
        self.assertEqual((data['sales_total'], data['orders_count'], data['average_ticket']), ('150.00', 2, '75.00'))
        self.assertEqual((data['expenses_total'], data['estimated_profit']), ('40.00', '110.00'))
        self.assertEqual((data['pending_delivery_count'], data['pending_collection_count'],
                          data['pending_collection_balance']), (1, 2, '100.00'))
        self.assertEqual(data['sales_criteria'], SALES_CRITERIA)

    def test_profit_is_reproducible_from_sales_and_expenses_and_ignores_collections(self):  # AC-12
        self.order(items=(('Pack', '100.00', 1),), paid='100.00')
        self.expense(self.category(), '30.00')
        data = self.get('dashboard')
        self.assertEqual(D(data['estimated_profit']), D(data['sales_total']) - D(data['expenses_total']))

    def test_negative_profit_and_empty_dashboard(self):  # AC-12, EDGE-03, EDGE-04
        empty = self.get('dashboard')
        self.assertEqual((empty['sales_total'], empty['expenses_total'], empty['estimated_profit'],
                          empty['average_ticket'], empty['orders_count']), ('0.00', '0.00', '0.00', None, 0))
        self.expense(self.category(), '25.00')
        self.assertEqual(self.get('dashboard')['estimated_profit'], '-25.00')

    def test_pending_counts_do_not_depend_on_the_period(self):  # AC-18, INV-10
        self.order(on=date(2020, 1, 1))
        for params in ({}, {'period': 'day'}, {'date_from': '2026-01-01', 'date_to': '2026-01-02'}):
            data = self.get('dashboard', **params)
            self.assertEqual((data['pending_delivery_count'], data['pending_collection_count']), (1, 1))


class SalesBreakdownApiTests(ReportingApiTestCase):
    def test_by_channel(self):  # AC-15
        self.order(channel='WHATSAPP', items=(('A', '10.00', 1),))
        self.order(channel='STORE', items=(('A', '100.00', 1),))
        self.order(channel='FAIR', status='CANCELLED')
        channels = self.get('sales-by-channel')['channels']
        self.assertEqual([(c['sales_channel'], c['orders_count'], c['total']) for c in channels],
                         [('STORE', 1, '100.00'), ('WHATSAPP', 1, '10.00')])

    def test_top_products_use_snapshots_and_amounts_before_discount(self):  # AC-16
        self.order(items=(('Pack', '35.00', 2), ('Chipa', '10.00', 5)), discount='20.00')
        data = self.get('top-products')
        self.assertEqual(data['limit'], 10)
        self.assertEqual([(p['product_name'], p['units'], p['amount']) for p in data['products']],
                         [('Chipa', 5, '50.00'), ('Pack', 2, '70.00')])

    def test_top_customers_have_names_and_skip_orders_without_customer(self):  # AC-17
        ana = CustomerModel.objects.create(name='Ana Pérez')
        luis = CustomerModel.objects.create(name='Luis')
        self.order(customer_id=ana.id, items=(('A', '50.00', 1),))
        self.order(customer_id=ana.id, items=(('A', '50.00', 1),))
        self.order(customer_id=luis.id, items=(('A', '30.00', 1),))
        self.order(customer_id=None, items=(('A', '999.00', 1),))
        data = self.get('top-customers')
        self.assertEqual([(c['name'], c['orders_count'], c['total']) for c in data['customers']],
                         [('Ana Pérez', 2, '100.00'), ('Luis', 1, '30.00')])
        self.assertEqual(data['customers'][0]['customer_id'], str(ana.id))


class PendingApiTests(ReportingApiTestCase):
    def test_delivered_and_partial_is_only_pending_collection(self):  # AC-18, EDGE-07
        ana = CustomerModel.objects.create(name='Ana')
        order = self.order(customer_id=ana.id, status='DELIVERED', paid='20.00', items=(('A', '70.00', 1),))
        data = self.get('pending')
        self.assertEqual(data['delivery'], {'count': 0, 'rows': []})
        self.assertEqual((data['collection']['count'], data['collection']['balance_total']), (1, '50.00'))
        row = data['collection']['rows'][0]
        self.assertEqual((row['id'], row['customer'], row['total'], row['balance'], row['payment_status']),
                         (str(order.id), {'id': str(ana.id), 'name': 'Ana'}, '70.00', '50.00', 'PARTIAL'))

    def test_delivery_rows_have_expected_date_and_nullable_customer(self):  # AC-18
        self.order(expected=date(2026, 10, 20), status='IN_PREPARATION', paid='70.00')
        row = self.get('pending')['delivery']['rows'][0]
        self.assertEqual((row['expected_delivery_date'], row['customer'], row['status']),
                         ('2026-10-20', None, 'IN_PREPARATION'))
        self.assertEqual(self.get('pending')['collection']['count'], 0)

    def test_cancelled_orders_and_lists_are_limited_to_ten(self):  # AC-18, EDGE-06
        self.order(status='CANCELLED', paid='10.00')
        for _ in range(12):
            self.order()
        data = self.get('pending')
        self.assertEqual((data['delivery']['count'], len(data['delivery']['rows'])), (12, 10))
        self.assertEqual((data['collection']['count'], len(data['collection']['rows'])), (12, 10))

    def test_empty(self):  # EDGE-03
        self.assertEqual(self.get('pending'), {
            'delivery': {'count': 0, 'rows': []},
            'collection': {'count': 0, 'balance_total': '0.00', 'rows': []},
        })
