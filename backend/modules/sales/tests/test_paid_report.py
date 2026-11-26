"""Reporte «Ingresos por venta»: pedidos entregados y pagados, filtros, paginación y exportación."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest import mock
from uuid import uuid4

from openpyxl import load_workbook
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.customers.infrastructure.django.models import CustomerModel
from modules.sales.domain.order import Order, OrderNumber
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository
from modules.sales.tests.periods import open_test_period

REPORT_URL = '/api/orders/paid-report/'
PERIOD_A, PERIOD_B = uuid4(), uuid4()


def _number(period_id, name, number) -> OrderNumber:
    return OrderNumber(period_id, name, number)


class PaidReportFixtures:
    counter = 0

    def make_order(self, company, total='100.00', paid='100.00', deliver=True, order_date=date(2026, 3, 10),
                   customer_id=None, period=(PERIOD_A, '2026')):
        PaidReportFixtures.counter += 1
        order = Order.create('WHATSAPP', order_date, customer_id)
        order.add_item(uuid4(), 'Pack', Decimal(total), 1)
        order.start_preparation(_number(period[0], period[1], PaidReportFixtures.counter))
        order.mark_ready()
        if deliver:
            order.deliver(order_date, date(2026, 12, 31))
        if Decimal(paid) > 0:
            order.register_payment(paid, 'CASH', order_date, '', date(2026, 12, 31))
        return DjangoOrderRepository(company.id).save(order)


class PaidReportApiTests(PaidReportFixtures, APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        open_test_period(self.company.id)
        authenticate(self.client, make_admin(self.company, username='ana'))

    def get(self, params='', status=200):
        response = self.client.get(f'{REPORT_URL}{params}')
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def test_only_delivered_and_paid_orders_of_the_company_appear(self):  # AC-01
        paid = self.make_order(self.company)
        self.make_order(self.company, paid='40.00')  # entregado, pago parcial
        self.make_order(self.company, paid='0')  # entregado, sin pago
        self.make_order(self.company, deliver=False)  # pagado, sin entregar
        other = make_company('Empresa B')
        self.make_order(other)
        data = self.get()
        self.assertEqual([row['id'] for row in data['results']], [str(paid.id)])
        self.assertEqual(set(data['results'][0]), {'id', 'code', 'order_date', 'customer', 'total', 'balance'})
        self.assertEqual(data['results'][0]['balance'], '0.00')

    def test_date_filters_are_inclusive_and_validated(self):  # AC-02
        early = self.make_order(self.company, order_date=date(2026, 1, 5))
        late = self.make_order(self.company, order_date=date(2026, 6, 5))
        ids = lambda data: {row['id'] for row in data['results']}  # noqa: E731
        self.assertEqual(ids(self.get('?date_from=2026-06-05')), {str(late.id)})
        self.assertEqual(ids(self.get('?date_to=2026-01-05')), {str(early.id)})
        self.assertEqual(ids(self.get()), {str(early.id), str(late.id)})
        error = self.get('?date_from=2026-06-05&date_to=2026-01-05', status=400)
        self.assertIn('date_to', error)
        self.assertIn('date_from', self.get('?date_from=ayer', status=400))

    def test_fiscal_period_filter(self):  # AC-03
        in_a = self.make_order(self.company, period=(PERIOD_A, '2026'))
        self.make_order(self.company, period=(PERIOD_B, '2027'))
        data = self.get(f'?fiscal_period_id={PERIOD_A}')
        self.assertEqual([row['id'] for row in data['results']], [str(in_a.id)])
        self.assertIn('fiscal_period_id', self.get('?fiscal_period_id=no-es-uuid', status=400))

    def test_pagination_and_totals_cover_the_whole_filtered_set(self):  # AC-04
        for _ in range(3):
            self.make_order(self.company, total='50.00', paid='50.00')
        data = self.get('?page_size=2')
        self.assertEqual((data['count'], len(data['results'])), (3, 2))
        self.assertEqual(data['totals'], {'orders_count': 3, 'total': '150.00', 'balance': '0.00'})
        self.assertEqual(len(self.get('?page_size=2&page=2')['results']), 1)

    def test_customer_name_is_resolved(self):
        customer = CustomerModel.objects.create(company_id=self.company.id, name='Ana Pérez')
        self.make_order(self.company, customer_id=customer.id)
        self.make_order(self.company)
        rows = {row['customer'] and row['customer']['name']: row for row in self.get()['results']}
        self.assertEqual(set(rows), {'Ana Pérez', None})

    def test_requires_authentication(self):  # AC-07
        self.client.credentials()
        self.assertEqual(self.client.get(REPORT_URL).status_code, 401)

    def test_company_without_the_sales_module_is_refused(self):  # AC-07
        with mock.patch('shared.module_gate.enabled_keys', return_value=set()):
            response = self.client.get(REPORT_URL)
            export = self.client.get(f'{REPORT_URL}export/xlsx/')
        self.assertEqual((response.status_code, export.status_code), (403, 403))
        self.assertEqual(response.json()['code'], 'module_disabled')


class PaidReportExportTests(PaidReportFixtures, APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        open_test_period(self.company.id)
        authenticate(self.client, make_admin(self.company, username='ana'))
        customer = CustomerModel.objects.create(company_id=self.company.id, name='Ana Pérez')
        self.first = self.make_order(self.company, total='120.50', paid='120.50', customer_id=customer.id)
        self.make_order(self.company, total='80.00', paid='80.00', order_date=date(2026, 1, 1))
        self.make_order(self.company, paid='10.00')  # no entra

    def test_excel_has_headers_rows_and_totals_with_the_filters(self):  # AC-05
        response = self.client.get(f'{REPORT_URL}export/xlsx/?date_from=2026-02-01')
        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml', response['Content-Type'])
        self.assertIn('attachment', response['Content-Disposition'])
        sheet = load_workbook(BytesIO(response.content)).active
        rows = [[cell.value for cell in row] for row in sheet.iter_rows()]
        self.assertEqual(rows[0], ['Pedido', 'Cliente', 'Total', 'Saldo'])
        self.assertEqual(rows[1], [self.first.code, 'Ana Pérez', 120.5, 0])
        self.assertEqual(rows[2], ['Totales', '1 pedidos', 120.5, 0])

    def test_pdf_is_a_pdf_attachment(self):  # AC-05
        response = self.client.get(f'{REPORT_URL}export/pdf/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_unknown_format_is_404_and_too_many_rows_is_400(self):  # AC-05
        self.assertEqual(self.client.get(f'{REPORT_URL}export/csv/').status_code, 404)
        with mock.patch('modules.sales.api.views.MAX_EXPORT_ROWS', 1):
            self.assertEqual(self.client.get(f'{REPORT_URL}export/xlsx/').status_code, 400)


class PaidReportHostileNamesTests(PaidReportFixtures, APITestCase):
    """Un nombre de cliente con marcado o fórmula no rompe ni ejecuta nada al exportar."""

    def setUp(self):
        self.company = make_company('Empresa A')
        open_test_period(self.company.id)
        authenticate(self.client, make_admin(self.company, username='ana'))
        formula = CustomerModel.objects.create(company_id=self.company.id, name='=HYPERLINK("http://x","a")')
        markup = CustomerModel.objects.create(company_id=self.company.id, name='Ana <b>x & <img src="y">')
        self.make_order(self.company, customer_id=formula.id)
        self.make_order(self.company, customer_id=markup.id)

    def test_excel_stores_a_formula_like_name_as_text(self):  # AC-05
        sheet = load_workbook(BytesIO(self.client.get(f'{REPORT_URL}export/xlsx/').content)).active
        cells = [cell for row in sheet.iter_rows(min_row=2, max_row=3, min_col=2, max_col=2) for cell in row]
        self.assertTrue(any(cell.value == '=HYPERLINK("http://x","a")' for cell in cells))
        self.assertEqual({cell.data_type for cell in cells}, {'s'})

    def test_pdf_survives_markup_in_names(self):  # AC-05
        response = self.client.get(f'{REPORT_URL}export/pdf/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'%PDF'))


class PaidReportExportRangeTests(PaidReportFixtures, APITestCase):
    def test_export_honours_date_range_and_period(self):  # AC-05
        self.company = make_company('Empresa A')
        open_test_period(self.company.id)
        authenticate(self.client, make_admin(self.company, username='ana'))
        self.make_order(self.company, order_date=date(2026, 7, 31), period=(PERIOD_A, 'Julio'))
        august = self.make_order(self.company, order_date=date(2026, 8, 15), period=(PERIOD_B, 'Agosto'))
        self.make_order(self.company, order_date=date(2026, 9, 1), period=(PERIOD_A, 'Julio'))
        for query in ('date_from=2026-08-01&date_to=2026-08-31', f'fiscal_period_id={PERIOD_B}'):
            for fmt in ('xlsx', 'pdf'):
                response = self.client.get(f'{REPORT_URL}export/{fmt}/?{query}')
                self.assertEqual(response.status_code, 200)
                if fmt == 'xlsx':
                    sheet = load_workbook(BytesIO(response.content)).active
                    codes = [row[0].value for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row - 1)]
                    self.assertEqual(codes, [august.code], query)
