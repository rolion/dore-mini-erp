"""CONT-12: API de configuración de asientos automáticos (API-01..04; AC-01..04, AC-10, AC-11)."""
from uuid import uuid4

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from modules.accounting.tests.test_api import ACCOUNTS, AccountingApiBase

URL = '/api/accounting/posting-config/'


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
        self.assertEqual([e['code'] for e in body['events']],
                         ['PURCHASE_RECOGNITION', 'PURCHASE_PAYMENT', 'PURCHASE_ADVANCE'])
        self.assertEqual([line['side'] for line in body['events'][0]['preview']], ['DEBIT', 'CREDIT', 'CREDIT'])
        self.assertEqual([r['role'] for r in body['roles']], ['INVENTORY', 'PAYABLE', 'SUPPLIER_ADVANCES'])
        self.assertEqual(len(body['methods']), 5)
        self.assertEqual(body['categories'], [])
        self.assertFalse(body['ready'])

    def test_unknown_or_missing_module_is_404(self):  # AC-01
        self.assertEqual(self.client_a.get(URL, {'module': 'customers'}).status_code, 404)
        self.assertEqual(self.client_a.get(URL).status_code, 404)

    def test_reading_does_not_scale_with_categories(self):  # NFR
        expense = self.make(self.client_a, 'Gastos', 'EXPENSE')
        for _ in range(6):
            self.client_a.put(f'{URL}categories/{uuid4()}/', {'account_id': expense['id']}, format='json')
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
        credit = body['events'][1]['preview'][2]  # reconocer la entrega: Haber Ingresos
        self.assertEqual((credit['status'], credit['account']['name']), ('ok', 'Ingresos'))
        self.assertEqual(self.put_role(self.client_a, 'SALES_INCOME', None).data['account'], None)

    def test_the_customer_advances_role_accepts_a_liability_and_rejects_other_classes(self):  # VEN-01 AC-01
        liability = self.make(self.client_a, 'Anticipos de clientes', 'LIABILITY')
        saved = self.put_role(self.client_a, 'CUSTOMER_ADVANCES', liability)
        self.assertEqual((saved.status_code, saved.data['account']['id']), (200, liability['id']))
        wrong_accounts = (self.make(self.client_a, 'Ingresos varios', 'INCOME'),
                          self.make(self.client_a, 'Caja general', 'ASSET'))
        for wrong in wrong_accounts:
            response = self.put_role(self.client_a, 'CUSTOMER_ADVANCES', wrong)
            self.assertEqual(response.status_code, 400)
            self.assertIn('Pasivo', response.json()['account_id'][0])
        body = self.client_a.get(URL, {'module': 'sales'}).json()
        self.assertEqual([e['code'] for e in body['events']], ['SALE_ADVANCE', 'SALE_DELIVERY', 'SALE_PAYMENT'])
        self.assertEqual(next(r for r in body['roles'] if r['role'] == 'CUSTOMER_ADVANCES')['account']['id'],
                         liability['id'])

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

    def test_a_400_carries_a_structured_problem_so_the_client_can_translate_it(self):  # REV-05
        expense = self.make(self.client_a, 'Gastos', 'EXPENSE')
        response = self.put_role(self.client_a, 'SALES_INCOME', expense)
        body = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body['problem'], {'code': 'wrong_class', 'params': {
            'account': 'Gastos', 'actual': 'EXPENSE', 'required': 'INCOME'}})
        self.assertIn('se requiere una cuenta de Ingresos', body['account_id'][0])  # respaldo en español
        method = self.assign(self.client_a, 'CASH', expense)  # también en el mapeo de métodos
        self.assertEqual((method.status_code, method.json()['problem']['code']), (400, 'wrong_class'))
        missing = self.client_a.put(f'{URL}roles/SALES_INCOME/', {'account_id': str(uuid4())}, format='json').json()
        self.assertEqual(missing['problem'], {'code': 'account_missing', 'params': {}})

    def test_issues_and_rows_expose_code_params_and_problem(self):  # REV-05
        body = self.client_a.get(URL, {'module': 'sales'}).json()
        first = next(i for i in body['events'][0]['issues'] if i['code'] == 'role_unconfigured')
        self.assertEqual((first['code'], first['role'], first['module'], first['problem']),
                         ('role_unconfigured', 'CUSTOMER_ADVANCES', 'sales', None))
        self.assertIn('Configúrela en Ventas', first['message'])
        method = next(i for i in body['events'][2]['issues'] if i['code'] == 'method_unconfigured')
        self.assertEqual(method['params'], {'method': 'Efectivo', 'method_code': 'CASH'})
        income = self.make(self.client_a, 'Ingresos viejos', 'INCOME')
        self.put_role(self.client_a, 'SALES_INCOME', income)
        self.client_a.post(f'{ACCOUNTS}{income["id"]}/deactivate/')
        body = self.client_a.get(URL, {'module': 'sales'}).json()
        row = next(r for r in body['roles'] if r['role'] == 'SALES_INCOME')
        self.assertEqual((row['problem']['code'], row['problem']['params']),
                         ('account_inactive', {'account': 'Ingresos viejos'}))
        invalid = next(i for e in body['events'] for i in e['issues'] if i['code'] == 'account_invalid')
        self.assertEqual(invalid['problem']['code'], 'account_inactive')
        self.assertIn('Corrija', invalid['message'])
        cash = next(m for m in body['methods'] if m['code'] == 'CASH')
        self.assertEqual(cash['problem']['code'], 'method_account_missing')

    def test_unknown_role_and_roles_with_another_source_are_404(self):
        for role in ('NOPE', 'MONEY', 'EXPENSE_BY_CATEGORY'):
            self.assertEqual(self.put_role(self.client_a, role, None).status_code, 404)

    def test_a_category_of_expenses_gets_an_expense_account_and_can_be_cleared(self):  # AC-02, AC-03
        expense = self.make(self.client_a, 'Gasto luz', 'EXPENSE')
        income = self.make(self.client_a, 'Ingresos', 'INCOME')
        theirs = self.make(self.client_b, 'Gasto B', 'EXPENSE')
        category = uuid4()
        url = f'{URL}categories/{category}/'
        for account in (income, theirs):
            response = self.client_a.put(url, {'account_id': account['id']}, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('account_id', response.json())
        ok = self.client_a.put(url, {'account_id': expense['id']}, format='json')
        self.assertEqual((ok.status_code, ok.data['category_id'], ok.data['account']['name']),
                         (200, str(category), 'Gasto luz'))
        listed = self.client_a.get(URL, {'module': 'expenses'}).json()['categories']
        self.assertEqual([(c['category_id'], c['account']['id']) for c in listed], [(str(category), expense['id'])])
        self.assertEqual(self.client_b.get(URL, {'module': 'expenses'}).json()['categories'], [])  # AC-10
        cleared = self.client_a.put(url, {'account_id': None}, format='json')
        self.assertEqual((cleared.status_code, cleared.data['account']), (200, None))
        self.assertEqual(self.client_a.get(URL, {'module': 'expenses'}).json()['categories'], [])
        self.assertEqual(self.client_a.put(f'{URL}categories/not-a-uuid/', {'account_id': None},
                                           format='json').status_code, 404)

    def test_a_method_only_accepts_asset_accounts_whatever_their_type(self):  # AC-04
        bank = self.create(self.client_a, 'Banco')
        self.assertEqual(self.assign(self.client_a, 'QR', bank).status_code, 200)
        untyped = self.make(self.client_a, 'Caja general', 'ASSET')  # Activo sin tipo Caja/Banco: sirve
        self.assertEqual(self.assign(self.client_a, 'CARD', untyped).status_code, 200)
        income = self.make(self.client_a, 'Ingresos', 'INCOME')
        expense = self.make(self.client_a, 'Gastos', 'EXPENSE')
        for account in (income, expense):
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
