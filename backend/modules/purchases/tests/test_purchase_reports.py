"""Reportes «Compras pagadas» y «Compras por pagar»: filtros, totales, acceso y exportación (BD real)."""
from io import BytesIO
from unittest import mock

from openpyxl import load_workbook

from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled
from modules.accounts.testing import authenticate, make_admin, make_company
from modules.purchases.infrastructure.django.models import PurchaseModel, SupplierModel
from modules.purchases.tests.test_payment_api import PaymentApiTestCase
from modules.purchases.tests.test_purchase_api import LIST_URL

PAID_URL = '/api/purchases/paid-report/'
PAYABLE_URL = '/api/purchases/payable-report/'


class PurchaseReportTests(PaymentApiTestCase):
    def scenario(self):
        """Borrador, cancelada, impaga, parcial y pagada."""
        draft = self.create(purchase_date='2026-10-01')
        cancelled = self.create(purchase_date='2026-10-02')
        self.client.post(f'{LIST_URL}{cancelled["id"]}/cancel/', {'reason': 'error'}, format='json')
        unpaid = self.confirmed_purchase()
        partial = self.confirmed_purchase()
        self.pay(partial, '20.00')
        paid = self.confirmed_purchase()
        self.pay(paid, '50.00')
        return {'draft': draft['id'], 'cancelled': cancelled['id'], 'unpaid': unpaid['id'],
                'partial': partial['id'], 'paid': paid['id']}

    def get(self, url, params=None, status=200):
        response = self.client.get(url, params or {})
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def ids(self, url, **params):
        return {row['id'] for row in self.get(url, params)['results']}

    def test_paid_report_has_only_confirmed_fully_paid_purchases(self):  # AC-01
        ids = self.scenario()
        data = self.get(PAID_URL)
        self.assertEqual({row['id'] for row in data['results']}, {ids['paid']})
        row = data['results'][0]
        self.assertEqual(set(row), {'id', 'code', 'order_date', 'customer', 'total', 'balance'})
        self.assertEqual((row['total'], row['balance'], row['customer']['name']), ('50.00', '0.00', self.supplier.name))
        self.assertRegex(row['code'], r'^NC-\d{6}$')
        self.assertEqual(data['totals'], {'orders_count': 1, 'total': '50.00', 'balance': '0.00'})  # AC-04

    def test_payable_report_has_confirmed_unpaid_and_partial_purchases(self):  # AC-01, AC-04
        ids = self.scenario()
        data = self.get(PAYABLE_URL)
        self.assertEqual({row['id'] for row in data['results']}, {ids['unpaid'], ids['partial']})
        balances = {row['id']: row['balance'] for row in data['results']}
        self.assertEqual((balances[ids['unpaid']], balances[ids['partial']]), ('50.00', '30.00'))
        self.assertEqual(data['totals'], {'orders_count': 2, 'total': '100.00', 'balance': '80.00'})

    def test_other_company_sees_nothing(self):  # AC-01, AC-07
        self.scenario()
        other = make_company('Otra')
        set_enabled(other, (*DEFAULT_ENABLED_KEYS, 'purchases'))
        authenticate(self.client, make_admin(other, username='otra'))
        for url in (PAID_URL, PAYABLE_URL):
            data = self.get(url)
            self.assertEqual((data['count'], data['totals']['orders_count']), (0, 0))

    def test_date_filters_and_validation(self):  # AC-02
        ids = self.scenario()
        PurchaseModel.objects.filter(pk=ids['unpaid']).update(purchase_date='2026-01-10')
        self.assertEqual(self.ids(PAYABLE_URL, date_to='2026-01-10'), {ids['unpaid']})
        self.assertEqual(self.ids(PAYABLE_URL, date_from='2026-02-01'), {ids['partial']})
        self.assertIn('date_to', self.get(PAYABLE_URL, {'date_from': '2026-02-01', 'date_to': '2026-01-01'}, 400))
        self.assertIn('date_from', self.get(PAYABLE_URL, {'date_from': 'ayer'}, 400))

    def test_fiscal_period_filter(self):  # AC-03
        ids = self.scenario()
        period_id = self.detail({'id': ids['unpaid']})['fiscal_period']['id']
        PurchaseModel.objects.filter(pk=ids['partial']).update(fiscal_period_id='11111111-1111-4111-8111-111111111111')
        self.assertEqual(self.ids(PAYABLE_URL, fiscal_period_id=period_id), {ids['unpaid']})
        self.assertIn('fiscal_period_id', self.get(PAYABLE_URL, {'fiscal_period_id': 'x'}, 400))

    def test_pagination_and_totals_cover_the_whole_set(self):  # AC-04
        self.scenario()
        data = self.get(PAYABLE_URL, {'page_size': 1})
        self.assertEqual((data['count'], len(data['results'])), (2, 1))
        self.assertEqual(data['totals']['orders_count'], 2)
        self.assertEqual((data['totals']['total'], data['totals']['balance']), ('100.00', '80.00'))

    def test_access_control(self):  # AC-07
        with mock.patch('shared.module_gate.enabled_keys', return_value=set()):
            for url in (PAID_URL, PAYABLE_URL, f'{PAID_URL}export/xlsx/'):
                self.assertEqual(self.client.get(url).status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get(PAID_URL).status_code, 401)

    def test_exports(self):  # AC-05
        ids = self.scenario()
        SupplierModel.objects.filter(pk=self.supplier.pk).update(name='=HYPERLINK("x")')
        response = self.client.get(f'{PAYABLE_URL}export/xlsx/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('compras-por-pagar-', response['Content-Disposition'])
        book = load_workbook(BytesIO(response.content))
        self.assertEqual(book.active.title, 'Compras por pagar')
        rows = [[cell.value for cell in row] for row in book.active.iter_rows()]
        self.assertEqual(rows[0], ['Compra', 'Proveedor', 'Total', 'Saldo'])
        self.assertEqual(len(rows), 4)  # encabezado, dos compras y totales
        self.assertEqual(rows[-1], ['Totales', '2 pedidos', 100, 80])
        self.assertEqual({row[1] for row in rows[1:3]}, {'=HYPERLINK("x")'})
        self.assertEqual({book.active.cell(row=2, column=2).data_type, book.active.cell(row=3, column=2).data_type},
                         {'s'})
        pdf = self.client.get(f'{PAID_URL}export/pdf/')
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertIn('compras-pagadas-', pdf['Content-Disposition'])
        self.assertEqual(self.client.get(f'{PAID_URL}export/csv/').status_code, 404)
        with mock.patch('modules.purchases.api.purchase_report_views.MAX_EXPORT_ROWS', 1):
            self.assertEqual(self.client.get(f'{PAYABLE_URL}export/xlsx/').status_code, 400)
        self.assertEqual(ids['paid'] in self.ids(PAID_URL), True)
