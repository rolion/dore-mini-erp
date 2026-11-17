"""CONT-12: API de configuración de asientos automáticos (API-01..04; AC-01..04, AC-10, AC-11)."""
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from modules.accounting.tests.test_api import ACCOUNTS, AccountingApiBase

URL = '/api/accounting/posting-config/'
CLASSIFICATIONS = '/api/accounting/classifications/'


class PostingApiBase(AccountingApiBase):
    def make(self, client, name, account_class, kind=None, code=None):
        body = {'name': name, 'currency': 'BOB', 'account_class': account_class,
                'code': code or str(900000 + len(name) * 7 + sum(map(ord, name)) % 1000)}
        if kind:
            body['kind'] = kind
        response = client.post(ACCOUNTS, body, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def put_role(self, client, role, account):
        return client.put(f'{URL}roles/{role}/', {'account_id': account['id'] if account else None}, format='json')


class ReadTests(PostingApiBase):
    def test_each_module_returns_only_its_events_with_preview(self):  # AC-01
        response = self.client_a.get(URL, {'module': 'purchases'})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['module'], 'purchases')
        self.assertFalse(body['accounting_enabled'])
        self.assertEqual([e['code'] for e in body['events']], ['PURCHASE_RECOGNITION', 'PURCHASE_PAYMENT'])
        self.assertEqual([line['side'] for line in body['events'][0]['preview']], ['DEBIT', 'CREDIT'])
        self.assertEqual([r['role'] for r in body['roles']], ['INVENTORY', 'PAYABLE'])
        self.assertEqual(len(body['methods']), 5)
        self.assertEqual(body['categories'], [])
        self.assertFalse(body['ready'])

    def test_unknown_or_missing_module_is_404(self):  # AC-01
        self.assertEqual(self.client_a.get(URL, {'module': 'customers'}).status_code, 404)
        self.assertEqual(self.client_a.get(URL).status_code, 404)

    def test_reading_does_not_scale_with_categories(self):  # NFR
        for index in range(6):
            self.client_a.post(CLASSIFICATIONS, {'name': f'Categoría {index}', 'direction': 'EXPENSE'}, format='json')
        with CaptureQueriesContext(connection) as queries:
            response = self.client_a.get(URL, {'module': 'expenses'})
        self.assertEqual(len(response.json()['categories']), 6)
        self.assertLessEqual(len(queries), 14)  # incluye sesión, usuario y permisos


class AssignTests(PostingApiBase):
    def test_a_valid_account_is_saved_previewed_and_can_be_cleared(self):  # AC-02
        income = self.make(self.client_a, 'Ingresos', 'INCOME')
        response = self.put_role(self.client_a, 'SALES_INCOME', income)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['account']['id'], income['id'])
        body = self.client_a.get(URL, {'module': 'sales'}).json()
        credit = body['events'][0]['preview'][1]
        self.assertEqual((credit['status'], credit['account']['name']), ('ok', 'Ingresos'))
        self.assertEqual(self.put_role(self.client_a, 'SALES_INCOME', None).data['account'], None)

    def test_foreign_wrong_class_or_inactive_accounts_are_rejected_with_a_field_error(self):  # AC-03
        theirs = self.make(self.client_b, 'Ingresos B', 'INCOME')
        expense = self.make(self.client_a, 'Gastos', 'EXPENSE')
        for account in (theirs, expense):
            response = self.put_role(self.client_a, 'SALES_INCOME', account)
            self.assertEqual(response.status_code, 400)
            self.assertIn('account_id', response.json())
        inactive = self.make(self.client_a, 'Ingresos viejos', 'INCOME')
        self.client_a.post(f'{ACCOUNTS}{inactive["id"]}/deactivate/')
        response = self.put_role(self.client_a, 'SALES_INCOME', inactive)
        self.assertEqual(response.status_code, 400)
        self.assertIn('deshabilitada', response.json()['account_id'][0])
        self.assertEqual(self.client_a.get(URL, {'module': 'sales'}).json()['roles'][1]['account'], None)

    def test_unknown_role_and_roles_with_another_source_are_404(self):
        for role in ('NOPE', 'MONEY', 'EXPENSE_BY_CATEGORY'):
            self.assertEqual(self.put_role(self.client_a, role, None).status_code, 404)

    def test_category_account_must_be_an_expense_account_for_an_expense_category(self):  # AC-03
        expense = self.make(self.client_a, 'Gasto luz', 'EXPENSE')
        income = self.make(self.client_a, 'Ingresos', 'INCOME')
        category = self.client_a.post(CLASSIFICATIONS, {'name': 'Luz', 'direction': 'EXPENSE'}, format='json').json()
        revenue = self.client_a.post(CLASSIFICATIONS, {'name': 'Cuotas', 'direction': 'INCOME'}, format='json').json()
        url = f'{URL}categories/{category["id"]}/'
        self.assertEqual(self.client_a.put(url, {'account_id': income['id']}, format='json').status_code, 400)
        ok = self.client_a.put(url, {'account_id': expense['id']}, format='json')
        self.assertEqual((ok.status_code, ok.data['account']['name']), (200, 'Gasto luz'))
        listed = self.client_a.get(URL, {'module': 'expenses'}).json()['categories']
        self.assertEqual([(c['name'], c['account']['id']) for c in listed], [('Luz', expense['id'])])
        self.assertEqual(self.client_a.put(f'{URL}categories/{revenue["id"]}/', {'account_id': None},
                                           format='json').status_code, 400)
        theirs = self.client_b.post(CLASSIFICATIONS, {'name': 'Otra', 'direction': 'EXPENSE'}, format='json').json()
        self.assertEqual(self.client_a.put(f'{URL}categories/{theirs["id"]}/', {'account_id': None},
                                           format='json').status_code, 404)

    def test_a_method_only_accepts_cash_or_bank_asset_accounts(self):  # AC-04
        bank = self.create(self.client_a, 'Banco')
        self.assertEqual(self.assign(self.client_a, 'QR', bank).status_code, 200)
        income = self.make(self.client_a, 'Ingresos', 'INCOME')
        receivable = self.make(self.client_a, 'Por cobrar', 'ASSET')  # Activo sin tipo Caja/Banco
        for account in (income, receivable):
            response = self.assign(self.client_a, 'CASH', account)
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn('account_id', response.json())
        body = self.client_a.get(URL, {'module': 'sales'}).json()
        self.assertEqual({m['code']: m['account'] and m['account']['name'] for m in body['methods']}['QR'], 'Banco')

    def test_company_isolation_and_access(self):  # AC-10, AC-11
        income = self.make(self.client_a, 'Ingresos', 'INCOME')
        self.put_role(self.client_a, 'SALES_INCOME', income)
        theirs = self.client_b.get(URL, {'module': 'sales'}).json()['roles']
        self.assertTrue(all(r['account'] is None for r in theirs))
        self.assertIn(APIClient().get(URL, {'module': 'sales'}).status_code, (401, 403))
        self.assertIn(APIClient().put(f'{URL}roles/RECEIVABLE/', {'account_id': None}, format='json').status_code,
                      (401, 403))

    def test_a_user_without_a_company_is_forbidden_on_every_route(self):  # AC-11
        from django.contrib.auth import get_user_model

        from modules.accounts.testing import authenticate
        lone = APIClient()
        authenticate(lone, get_user_model().objects.create_user(username='solo', password='x-Pass-123'))
        self.assertEqual(lone.get(URL, {'module': 'sales'}).status_code, 403)
        self.assertEqual(lone.put(f'{URL}roles/RECEIVABLE/', {'account_id': None}, format='json').status_code, 403)
        self.assertEqual(lone.put(f'{URL}categories/{"0" * 8}-0000-0000-0000-{"0" * 12}/', {'account_id': None},
                                  format='json').status_code, 403)
        self.assertEqual(APIClient().get(URL, {'module': 'sales'}).status_code, 401)
