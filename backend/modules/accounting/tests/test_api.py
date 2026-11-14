"""PB-ACC-001: API de cuentas, mapeo método → cuenta y precondición de habilitación (AC-01..06)."""
from rest_framework.test import APIClient, APITestCase

from modules.accounting import services
from modules.accounting.infrastructure.django.models import AccountModel
from modules.accounts.testing import authenticate, make_admin, make_company
from modules.modularity.infrastructure.django.models import CompanyModuleModel

ACCOUNTS = '/api/accounting/accounts/'
METHODS = '/api/accounting/payment-methods/'


class AccountingApiBase(APITestCase):
    def setUp(self):
        self.company_a = make_company('A')
        self.company_b = make_company('B')
        self.client_a = self.login(make_admin(self.company_a, 'ana'))
        self.client_b = self.login(make_admin(self.company_b, 'beto'))

    @staticmethod
    def login(user):
        client = APIClient()
        authenticate(client, user)
        return client

    def create(self, client, name, currency='BOB'):
        response = client.post(ACCOUNTS, {'name': name, 'currency': currency}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def assign(self, client, code, account, active=True):
        return client.put(f'{METHODS}{code}/', {'account_id': account['id'] if account else None,
                                                'is_active': active}, format='json')


class AccountTests(AccountingApiBase):
    def test_companies_configure_their_own_destinations(self):  # AC-01
        caja, banco = self.create(self.client_a, 'Caja'), self.create(self.client_a, 'Banco')
        self.assertEqual(self.assign(self.client_a, 'CASH', caja).status_code, 200)
        self.assertEqual(self.assign(self.client_a, 'BANK_TRANSFER', banco).status_code, 200)
        self.assertEqual(self.assign(self.client_a, 'QR', banco).status_code, 200)
        own = self.create(self.client_b, 'Caja chica')
        self.assertEqual(self.assign(self.client_b, 'CASH', own).status_code, 200)
        by_code = {m['code']: m for m in self.client_a.get(METHODS).data}
        self.assertEqual(by_code['CASH']['account']['name'], 'Caja')
        self.assertEqual(by_code['QR']['account']['name'], 'Banco')
        self.assertIsNone(by_code['CARD']['account'])
        self.assertEqual({a['name'] for a in self.client_b.get(ACCOUNTS).data}, {'Caja chica'})
        self.assertEqual({m['code']: m['account']['name'] for m in self.client_b.get(METHODS).data
                          if m['account']}, {'CASH': 'Caja chica'})

    def test_methods_start_active_and_unmapped_and_no_account_is_created(self):  # INV-07
        self.assertEqual(self.client_a.get(ACCOUNTS).data, [])
        methods = self.client_a.get(METHODS).data
        self.assertEqual([m['code'] for m in methods], ['CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'])
        self.assertTrue(all(m['is_active'] and m['account'] is None for m in methods))

    def test_rejects_foreign_account_foreign_currency_and_inactive_account(self):  # AC-02
        foreign = self.create(self.client_b, 'Ajena')
        self.assertEqual(self.assign(self.client_a, 'CASH', foreign).status_code, 404)
        usd = self.create(self.client_a, 'Dólares', 'USD')
        self.assertEqual(self.assign(self.client_a, 'CASH', usd).status_code, 400)
        old = self.create(self.client_a, 'Vieja')
        self.client_a.post(f'{ACCOUNTS}{old["id"]}/deactivate/')
        self.assertEqual(self.assign(self.client_a, 'CASH', old).status_code, 400)
        self.assertEqual(self.client_a.get(f'{ACCOUNTS}{foreign["id"]}/').status_code, 404)
        self.assertEqual(self.client_a.put(f'{METHODS}NOPE/', {'account_id': None}, format='json').status_code, 404)

    def test_duplicate_names_are_rejected_case_insensitively(self):  # EDGE-01
        self.create(self.client_a, 'Caja')
        response = self.client_a.post(ACCOUNTS, {'name': ' caja ', 'currency': 'BOB'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.data)
        self.create(self.client_b, 'Caja')  # otra empresa puede repetirlo

    def test_deactivating_an_account_in_use_is_blocked_until_reassigned(self):  # AC-03
        banco = self.create(self.client_a, 'Banco')
        self.assign(self.client_a, 'QR', banco)
        response = self.client_a.post(f'{ACCOUNTS}{banco["id"]}/deactivate/')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'account_in_use')
        self.assertEqual(response.data['methods'], ['QR'])
        self.assertEqual(self.assign(self.client_a, 'QR', None, active=False).status_code, 200)
        self.assertEqual(self.client_a.post(f'{ACCOUNTS}{banco["id"]}/deactivate/').status_code, 200)

    def test_changing_currency_of_an_account_in_use_is_blocked(self):
        banco = self.create(self.client_a, 'Banco')
        self.assign(self.client_a, 'QR', banco)
        response = self.client_a.patch(f'{ACCOUNTS}{banco["id"]}/', {'currency': 'USD'}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(AccountModel.objects.get(pk=banco['id']).currency, 'BOB')

    def test_changing_the_destination_updates_the_current_account(self):  # AC-04
        banco_a, banco_b = self.create(self.client_a, 'Banco A'), self.create(self.client_a, 'Banco B')
        self.assign(self.client_a, 'BANK_TRANSFER', banco_a)
        self.assertEqual(services.resolve_account(self.company_a.id, 'BANK_TRANSFER').name, 'Banco A')
        self.assign(self.client_a, 'BANK_TRANSFER', banco_b)
        self.assertEqual(services.resolve_account(self.company_a.id, 'BANK_TRANSFER').name, 'Banco B')
        self.assertEqual(AccountModel.objects.filter(company_id=self.company_a.id).count(), 2)  # Banco A se conserva
        self.assertIsNone(services.resolve_account(self.company_b.id, 'BANK_TRANSFER'))
        self.assertIsNone(services.resolve_account(self.company_a.id, 'CASH'))

    def test_inactive_method_does_not_resolve(self):
        caja = self.create(self.client_a, 'Caja')
        self.assign(self.client_a, 'CASH', caja, active=False)
        self.assertIsNone(services.resolve_account(self.company_a.id, 'CASH'))

    def test_only_authenticated_company_users_can_use_the_api(self):  # AC-06
        anonymous = APIClient()
        self.assertIn(anonymous.get(ACCOUNTS).status_code, (401, 403))
        self.assertIn(anonymous.get(METHODS).status_code, (401, 403))
        from django.contrib.auth import get_user_model
        sin_empresa = APIClient()
        authenticate(sin_empresa, get_user_model().objects.create_user(username='solo', password='x-Pass-123'))
        self.assertEqual(sin_empresa.get(ACCOUNTS).status_code, 403)
        self.assertEqual(sin_empresa.put(f'{METHODS}CASH/', {'account_id': None}, format='json').status_code, 403)


class EnableAccountingTests(AccountingApiBase):
    def enable(self, client=None):
        return (client or self.client_a).post('/api/modules/accounting/enable/')

    def test_blocked_until_every_active_method_has_a_destination(self):  # AC-05
        response = self.enable()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'incomplete_configuration')
        self.assertEqual(response.data['missing'], ['Efectivo', 'QR', 'Transferencia', 'Tarjeta', 'Otro'])
        caja = self.create(self.client_a, 'Caja')
        for code in ('CASH', 'QR', 'BANK_TRANSFER', 'CARD'):
            self.assign(self.client_a, code, caja)
        response = self.enable()
        self.assertEqual((response.status_code, response.data['missing']), (409, ['Otro']))
        self.assign(self.client_a, 'OTHER', None, active=False)
        self.assertEqual(self.enable().status_code, 200)
        self.assertTrue(CompanyModuleModel.objects.filter(company_id=self.company_a.id, module_key='accounting').exists())

    def test_default_behaviour_is_unchanged_and_other_company_is_unaffected(self):
        keys = {m['key']: m['enabled'] for m in self.client_a.get('/api/modules/').data}
        self.assertFalse(keys['accounting'])
        self.assertEqual(self.enable(self.client_b).status_code, 409)
        self.assertFalse(CompanyModuleModel.objects.filter(module_key='accounting').exists())
