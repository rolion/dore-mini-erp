"""CONT-08: seis clasificaciones contables fijas, habilitables por empresa (AC-01..AC-08; INV-01..INV-04)."""
import itertools
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TransactionTestCase
from rest_framework.test import APIClient, APITestCase

from modules.accounting import services
from modules.accounting.domain.account import AccountValidationError
from modules.accounting.domain.account_class import ACCOUNT_CLASSES, AccountClassNotFound, parse_account_class
from modules.accounting.infrastructure.django.models import AccountClassSettingModel, AccountModel, EntryModel
from modules.accounts.testing import authenticate, make_admin, make_company

CODES = itertools.count(1)
ACCOUNTS = '/api/accounting/accounts/'
CLASSES = '/api/accounting/account-classes/'
SIX = ['ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE', 'COST']


class DomainTests(SimpleTestCase):
    def test_catalog_is_exactly_the_six_in_fixed_order(self):  # INV-01
        self.assertEqual(list(ACCOUNT_CLASSES), SIX)

    def test_parse_normalizes_and_rejects_unknown(self):
        self.assertEqual(parse_account_class(' cost '), 'COST')
        for bad in ('OTHER', '', None, 5):
            with self.assertRaises(AccountClassNotFound):
                parse_account_class(bad)


class ApiBase(APITestCase):
    def setUp(self):
        self.company_a, self.company_b = make_company('A'), make_company('B')
        self.client_a = self.login(make_admin(self.company_a, 'ana'))
        self.client_b = self.login(make_admin(self.company_b, 'beto'))

    @staticmethod
    def login(user):
        client = APIClient()
        authenticate(client, user)
        return client

    def create_account(self, client, name='Caja', **extra):
        payload = {'name': name, 'currency': 'BOB', 'code': str(next(CODES) + 900000), 'account_class': 'ASSET', **extra}
        if payload['account_class'] == 'ASSET':
            payload.setdefault('kind', 'CASH')  # solo las cuentas de Activo pueden ser de dinero
        return client.post(ACCOUNTS, payload, format='json')

    def set_state(self, client, code, action):
        return client.post(f'{CLASSES}{code}/{action}/')


class ListTests(ApiBase):
    def test_lists_exactly_six_enabled_by_default_without_rows(self):  # AC-01
        response = self.client_a.get(CLASSES)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c['code'] for c in response.data], SIX)
        self.assertTrue(all(c['enabled'] for c in response.data))
        self.assertIn('INCOME', [c['code'] for c in response.data])
        self.assertEqual(AccountClassSettingModel.objects.count(), 0)

    def test_no_create_rename_or_delete_routes(self):  # AC-04
        self.assertEqual(self.client_a.post(CLASSES, {'code': 'OTHER'}, format='json').status_code, 405)
        self.assertEqual(self.client_a.patch(f'{CLASSES}COST/', {'code': 'X'}, format='json').status_code, 404)
        self.assertEqual(self.client_a.delete(f'{CLASSES}COST/').status_code, 404)
        self.assertEqual(self.client_a.get(CLASSES).data.__len__(), 6)


class ToggleTests(ApiBase):
    def test_disable_is_per_company(self):  # AC-02
        self.assertEqual(self.set_state(self.client_a, 'COST', 'disable').data, {'code': 'COST', 'enabled': False})
        states_a = {c['code']: c['enabled'] for c in self.client_a.get(CLASSES).data}
        states_b = {c['code']: c['enabled'] for c in self.client_b.get(CLASSES).data}
        self.assertFalse(states_a['COST'])
        self.assertTrue(states_b['COST'])
        rejected = self.create_account(self.client_a, 'Costos', account_class='COST')
        self.assertEqual(rejected.status_code, 400)
        self.assertIn('account_class', rejected.data)
        self.assertEqual(self.create_account(self.client_b, 'Costos', account_class='COST').status_code, 201)

    def test_enable_restores_and_is_idempotent(self):  # AC-05
        for _ in range(2):
            self.set_state(self.client_a, 'COST', 'disable')
        self.assertEqual(AccountClassSettingModel.objects.filter(company_id=self.company_a.id).count(), 1)
        for _ in range(2):
            self.assertTrue(self.set_state(self.client_a, 'cost', 'enable').data['enabled'])
        self.assertEqual(AccountClassSettingModel.objects.filter(company_id=self.company_a.id).count(), 1)
        self.assertEqual(self.create_account(self.client_a, 'Costos', account_class='COST').status_code, 201)

    def test_unknown_code_is_404(self):  # AC-05
        self.assertEqual(self.set_state(self.client_a, 'OTHER', 'disable').status_code, 404)
        self.assertEqual(AccountClassSettingModel.objects.count(), 0)

    def test_requires_authentication_and_company(self):  # AC-06
        self.assertIn(APIClient().get(CLASSES).status_code, (401, 403))
        self.assertIn(APIClient().post(f'{CLASSES}COST/disable/').status_code, (401, 403))
        no_company = self.login(get_user_model().objects.create_user(username='solo', password='x-Pass-123'))
        self.assertEqual(no_company.get(CLASSES).status_code, 403)
        self.assertEqual(self.set_state(no_company, 'COST', 'disable').status_code, 403)

    def test_other_company_cannot_change_state_of_a(self):  # AC-06
        self.set_state(self.client_b, 'COST', 'disable')
        self.assertTrue({c['code']: c['enabled'] for c in self.client_a.get(CLASSES).data}['COST'])


class AccountClassificationTests(ApiBase):
    def test_account_exposes_and_accepts_enabled_class(self):  # API-03, CONT-09 AC-02
        created = self.create_account(self.client_a, account_class='asset')
        self.assertEqual((created.status_code, created.data['account_class']), (201, 'ASSET'))
        missing = self.client_a.post(ACCOUNTS, {'name': 'Sin clase', 'currency': 'BOB', 'code': '999'}, format='json')
        self.assertEqual(missing.status_code, 400)  # CONT-09: la clasificación es obligatoria al crear
        self.assertIn('account_class', missing.data)
        bad = self.create_account(self.client_a, 'Mala', account_class='OTHER')
        self.assertEqual(bad.status_code, 400)

    def test_patch_to_disabled_class_is_rejected(self):  # AC-02
        account = self.create_account(self.client_a).data
        self.set_state(self.client_a, 'EXPENSE', 'disable')
        response = self.client_a.patch(f'{ACCOUNTS}{account["id"]}/', {'account_class': 'EXPENSE'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AccountModel.objects.get(pk=account['id']).account_class, 'ASSET')

    def test_existing_account_of_disabled_class_keeps_everything(self):  # AC-03, INV-03, INV-04
        account = self.create_account(self.client_a, 'Costos', account_class='COST').data
        entry = EntryModel.objects.create(
            company_id=self.company_a.id, account_id=account['id'], currency='BOB', amount=Decimal('80.00'),
            payment_date=date(2026, 11, 1), payment_method='CASH', origin_kind='PRODUCT', origin_id=uuid4())
        before_balance = services.account_balances(self.company_a.id)
        before_entry = EntryModel.objects.filter(pk=entry.pk).values().get()

        self.set_state(self.client_a, 'COST', 'disable')

        stored = AccountModel.objects.get(pk=account['id'])
        self.assertEqual((stored.account_class, stored.is_active), ('COST', True))
        self.assertEqual(EntryModel.objects.filter(pk=entry.pk).values().get(), before_entry)
        self.assertEqual(services.account_balances(self.company_a.id), before_balance)
        detail = self.client_a.get(f'{ACCOUNTS}{account["id"]}/').data
        self.assertEqual(detail['account_class'], 'COST')
        renamed = self.client_a.patch(f'{ACCOUNTS}{account["id"]}/',
                                      {'name': 'Costos 2', 'account_class': 'COST'}, format='json')
        self.assertEqual((renamed.status_code, renamed.data['account_class']), (200, 'COST'))
        self.assertEqual(self.client_a.post(f'{ACCOUNTS}{account["id"]}/deactivate/').data['is_active'], False)
        self.assertEqual(self.client_a.post(f'{ACCOUNTS}{account["id"]}/activate/').data['is_active'], True)
        self.assertEqual(AccountClassSettingModel.objects.count(), 1)

    def test_facade_validates_for_new_uses(self):
        self.set_state(self.client_a, 'COST', 'disable')
        self.assertEqual(services.validate_account_class(self.company_a.id, 'income'), 'INCOME')
        with self.assertRaises(AccountValidationError):
            services.validate_account_class(self.company_a.id, 'COST')
        self.assertEqual(services.validate_account_class(self.company_b.id, 'COST'), 'COST')
        with self.assertRaises(AccountValidationError):
            services.validate_account_class(self.company_a.id, 'OTHER')


BEFORE = [('accounting', '0006_entry_direction_operation_reversal')]
AFTER = [('accounting', '0007_account_class')]


class MigrationTests(TransactionTestCase):
    def migrate(self, targets):
        MigrationExecutor(connection).migrate(targets)
        return MigrationExecutor(connection).loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_0007_keeps_existing_data_and_is_reversible(self):  # AC-08
        old = self.migrate(BEFORE)
        company = uuid4()
        account = old.get_model('accounting', 'AccountModel').objects.create(
            company_id=company, name='Banco', currency='BOB', kind='BANK', opening_balance=Decimal('100.50'))
        new = self.migrate(AFTER)
        kept = new.get_model('accounting', 'AccountModel').objects.get(pk=account.pk)
        self.assertEqual((kept.name, kept.kind, kept.opening_balance, kept.account_class),
                         ('Banco', 'BANK', Decimal('100.50'), None))
        self.assertEqual(new.get_model('accounting', 'AccountClassSettingModel').objects.count(), 0)
        back = self.migrate(BEFORE)
        self.assertEqual(back.get_model('accounting', 'AccountModel').objects.get(pk=account.pk).name, 'Banco')
