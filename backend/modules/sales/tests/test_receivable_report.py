"""Reporte «Pedidos por cobrar»: pedidos no cancelados ni devueltos con saldo pendiente."""
from datetime import date, datetime, timezone
from io import BytesIO
from unittest import mock

from openpyxl import load_workbook
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.customers.infrastructure.django.models import CustomerModel
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository
from modules.sales.tests.periods import open_test_period
from modules.sales.tests.test_paid_report import PERIOD_A, PERIOD_B, PaidReportFixtures

URL = '/api/orders/receivable-report/'


class ReceivableReportTests(PaidReportFixtures, APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        open_test_period(self.company.id)
        authenticate(self.client, make_admin(self.company, username='ana'))

    def get(self, params='', status=200):
        response = self.client.get(f'{URL}{params}')
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def cancelled_with_balance(self):
        repository = DjangoOrderRepository(self.company.id)
        order = self.make_order(self.company, paid='0', deliver=False)
        loaded = repository.get(order.id)
        loaded.cancel('prueba', datetime(2026, 12, 1, tzinfo=timezone.utc))
        return repository.save(loaded)

    def test_only_orders_with_a_balance_that_are_not_cancelled_appear(self):  # AC-01
        unpaid_delivered = self.make_order(self.company, paid='0')
        partial_open = self.make_order(self.company, paid='40.00', deliver=False)
        self.make_order(self.company)  # pagado por completo
        self.cancelled_with_balance()
        self.make_order(make_company('Empresa B'), paid='0')
        data = self.get()
        self.assertEqual({row['id'] for row in data['results']}, {str(unpaid_delivered.id), str(partial_open.id)})
        balances = {row['id']: row['balance'] for row in data['results']}
        self.assertEqual(balances[str(unpaid_delivered.id)], '100.00')
        self.assertEqual(balances[str(partial_open.id)], '60.00')
        self.assertEqual(data['totals'], {'orders_count': 2, 'total': '200.00', 'balance': '160.00'})  # AC-04

    def test_date_and_period_filters_and_validation(self):  # AC-02, AC-03
        early = self.make_order(self.company, paid='0', order_date=date(2026, 1, 5), period=(PERIOD_A, '2026'))
        late = self.make_order(self.company, paid='0', order_date=date(2026, 6, 5), period=(PERIOD_B, '2027'))
        ids = lambda data: {row['id'] for row in data['results']}  # noqa: E731
        self.assertEqual(ids(self.get('?date_from=2026-06-05')), {str(late.id)})
        self.assertEqual(ids(self.get('?date_to=2026-01-05')), {str(early.id)})
        self.assertEqual(ids(self.get(f'?fiscal_period_id={PERIOD_A}')), {str(early.id)})
        self.assertIn('date_to', self.get('?date_from=2026-06-05&date_to=2026-01-05', status=400))
        self.assertIn('fiscal_period_id', self.get('?fiscal_period_id=x', status=400))

    def test_pagination(self):  # AC-04
        for _ in range(3):
            self.make_order(self.company, paid='0')
        data = self.get('?page_size=2')
        self.assertEqual((data['count'], len(data['results'])), (3, 2))

    def test_customer_name(self):
        customer = CustomerModel.objects.create(company_id=self.company.id, name='Ana Pérez')
        self.make_order(self.company, paid='0', customer_id=customer.id)
        self.assertEqual(self.get()['results'][0]['customer']['name'], 'Ana Pérez')

    def test_access_control(self):  # AC-07
        with mock.patch('shared.module_gate.enabled_keys', return_value=set()):
            self.assertEqual(self.client.get(URL).status_code, 403)
            self.assertEqual(self.client.get(f'{URL}export/pdf/').status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_exports_use_the_receivable_title_and_filters(self):  # AC-05
        customer = CustomerModel.objects.create(company_id=self.company.id, name='Ana Pérez')
        owing = self.make_order(self.company, paid='0', total='80.00', customer_id=customer.id)
        self.make_order(self.company, paid='0', order_date=date(2026, 1, 1))
        response = self.client.get(f'{URL}export/xlsx/?date_from=2026-02-01')
        self.assertEqual(response.status_code, 200)
        self.assertIn('pedidos-por-cobrar-', response['Content-Disposition'])
        book = load_workbook(BytesIO(response.content))
        self.assertEqual(book.active.title, 'Pedidos por cobrar')
        rows = [[c.value for c in row] for row in book.active.iter_rows()]
        self.assertEqual(rows[1], [owing.code, 'Ana Pérez', 80, 80])
        self.assertEqual(rows[2], ['Totales', '1 pedidos', 80, 80])
        pdf = self.client.get(f'{URL}export/pdf/')
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertEqual(self.client.get(f'{URL}export/csv/').status_code, 404)
        with mock.patch('modules.sales.api.views.MAX_EXPORT_ROWS', 1):
            self.assertEqual(self.client.get(f'{URL}export/xlsx/').status_code, 400)
