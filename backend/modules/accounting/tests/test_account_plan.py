"""CONT-09: plan de cuentas con código, clasificación obligatoria, tipo de dinero opcional y cuenta correctora."""
import itertools
from unittest import mock
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test.utils import CaptureQueriesContext
from django.test import SimpleTestCase, TransactionTestCase
from rest_framework.test import APIClient, APITestCase

from modules.accounting import services
from modules.accounting.domain.account import Account, AccountValidationError, validate_code
from modules.accounting.infrastructure.django.models import AccountModel, EntryModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounts.testing import authenticate, make_admin, make_company

ACCOUNTS = '/api/accounting/accounts/'
METHODS = '/api/accounting/payment-methods/'
SEQ = itertools.count(1)


class DomainTests(SimpleTestCase):
    def test_code_rules(self):  # INV-01
        self.assertEqual(validate_code('  111001 '), '111001')
        self.assertEqual(validate_code('001'), '001')  # los ceros a la izquierda se conservan
        for bad in ('', '   ', None, '1' * 21, '1 1', '1.1.1.001', 'A1', '1-2', '１２', '1/2'):
            with self.assertRaises(AccountValidationError) as raised:
                validate_code(bad)
            self.assertIn('code', raised.exception.errors)

    def test_kind_only_for_asset(self):  # INV-04
        asset = Account.create('Caja', 'BOB', 'CASH', code='111001')
        asset.account_class = 'ASSET'
        asset.ensure_consistent()
        expense = Account.create('Alquiler', 'BOB', 'CASH', code='611002')
        expense.account_class = 'EXPENSE'
        with self.assertRaises(AccountValidationError) as raised:
            expense.ensure_consistent()
        self.assertIn('kind', raised.exception.errors)
        legacy = Account.create('Vieja', 'BOB', 'CASH')  # sin clasificación todavía: se tolera
        legacy.ensure_consistent()


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

    def create(self, client, name='Caja', code=None, account_class='ASSET', **extra):
        payload = {'name': name, 'currency': 'BOB', 'code': code or str(next(SEQ) + 900000), 'account_class': account_class, **extra}
        return client.post(ACCOUNTS, payload, format='json')

    def add_entry(self, account_id, company):
        return EntryModel.objects.create(
            company_id=company.id, account_id=account_id, currency='BOB', amount=Decimal('50.00'),
            payment_date=date(2026, 11, 1), payment_method='CASH', origin_kind='PRODUCT', origin_id=uuid4())


class CreateTests(ApiBase):
    def test_creates_account_and_code_is_unique_per_company(self):  # AC-01
        created = self.create(self.client_a, 'Caja', '101', kind='CASH')
        self.assertEqual((created.status_code, created.data['code'], created.data['account_class']), (201, '101', 'ASSET'))
        for repeated in ('101', ' 101 '):
            dup = self.create(self.client_a, 'Otra', repeated)
            self.assertEqual(dup.status_code, 400)
            self.assertIn('code', dup.data)
        self.assertEqual(self.create(self.client_a, 'Otra 2', '1001').status_code, 201)
        self.assertEqual(self.create(self.client_a, 'Otra 3', '001').status_code, 201)  # '001' y '1' son códigos distintos
        self.assertEqual(self.create(self.client_a, 'Otra 4', '1').status_code, 201)
        self.assertEqual(self.create(self.client_b, 'Caja', '101', kind='CASH').status_code, 201)  # otra empresa

    def test_code_is_numeric_only_and_each_company_can_use_the_same_one(self):  # INV-01, AC-01
        for bad in ('1.1.1.001', 'A111', '111-001', '11 1001'):
            rejected = self.create(self.client_a, 'Caja', bad)
            self.assertEqual(rejected.status_code, 400, bad)
            self.assertIn('code', rejected.data)
        caja_a = self.create(self.client_a, 'Caja', '111001', kind='CASH')
        caja_b = self.create(self.client_b, 'Caja', '111001', kind='CASH')  # otra empresa, mismo código
        self.assertEqual((caja_a.status_code, caja_b.status_code, caja_b.data['code']), (201, 201, '111001'))
        self.assertEqual(self.create(self.client_a, 'Caja chica', '111001').status_code, 400)  # misma empresa

    def test_requires_code_and_classification_enabled(self):  # AC-02
        base = {'name': 'X', 'currency': 'BOB'}
        no_code = self.client_a.post(ACCOUNTS, {**base, 'account_class': 'ASSET'}, format='json')
        no_class = self.client_a.post(ACCOUNTS, {**base, 'code': '999001'}, format='json')
        self.assertIn('code', no_code.data)
        self.assertIn('account_class', no_class.data)
        self.assertEqual((no_code.status_code, no_class.status_code), (400, 400))
        self.client_a.post('/api/accounting/account-classes/COST/disable/')
        disabled = self.create(self.client_a, 'Costos', '999002', 'COST')
        self.assertEqual(disabled.status_code, 400)
        self.assertIn('account_class', disabled.data)
        self.assertEqual(AccountModel.objects.filter(company_id=self.company_a.id).count(), 0)

    def test_kind_only_with_asset_and_contra_flag(self):  # AC-05, AC-06
        bad = self.create(self.client_a, 'Alquiler', '611002', 'EXPENSE', kind='CASH')
        self.assertEqual(bad.status_code, 400)
        self.assertIn('kind', bad.data)
        self.assertEqual(self.create(self.client_a, 'Alquiler', '611002', 'EXPENSE').status_code, 201)
        contra = self.create(self.client_a, 'Depreciación acumulada', '121005', is_contra=True)
        self.assertEqual((contra.status_code, contra.data['is_contra'], contra.data['kind']), (201, True, None))
        self.assertFalse(self.create(self.client_a, 'Equipos', '121002').data['is_contra'])

    def test_duplicate_code_is_a_400_for_sequential_requests(self):  # EDGE
        self.create(self.client_a, 'Caja', '101')
        again = self.create(self.client_a, 'Caja 2', '101')
        self.assertEqual(again.status_code, 400)

    def test_race_on_duplicate_code_is_resolved_by_the_unique_constraint(self):  # EDGE, REV-04
        """La comprobación previa no ve el duplicado (otra petición lo inserta a la vez): manda la restricción única."""
        self.create(self.client_a, 'Caja', '777')
        repository = DjangoAccountRepository(self.company_a.id)
        racing = Account.create('Banco', 'BOB', code='777')
        with mock.patch.object(DjangoAccountRepository, '_conflicts', side_effect=[{}, {'code': ['Ya existe una cuenta con ese código.']}]):
            with self.assertRaises(AccountValidationError) as raised:
                repository.save(racing)
        self.assertEqual(raised.exception.errors, {'code': ['Ya existe una cuenta con ese código.']})
        self.assertEqual(AccountModel.objects.filter(company_id=self.company_a.id, code='777').count(), 1)
        self.assertFalse(AccountModel.objects.filter(pk=racing.id).exists())


class UpdateTests(ApiBase):
    def test_rename_and_recode_always_allowed_but_class_locked_by_entries(self):  # AC-04, INV-05
        account = self.create(self.client_a, 'Caja', '101', kind='CASH').data
        entry = self.add_entry(account['id'], self.company_a)
        url = f'{ACCOUNTS}{account["id"]}/'
        before = EntryModel.objects.filter(pk=entry.pk).values().get()
        blocked = self.client_a.patch(url, {'account_class': 'LIABILITY'}, format='json')
        self.assertEqual((blocked.status_code, blocked.data['code']), (409, 'account_has_entries'))
        self.assertEqual(AccountModel.objects.get(pk=account['id']).account_class, 'ASSET')
        renamed = self.client_a.patch(url, {'name': 'Caja chica', 'code': '111001'}, format='json')
        self.assertEqual((renamed.status_code, renamed.data['name'], renamed.data['code']), (200, 'Caja chica', '111001'))
        same = self.client_a.patch(url, {'account_class': 'ASSET'}, format='json')
        self.assertEqual(same.status_code, 200)  # no es un cambio
        self.assertEqual(EntryModel.objects.filter(pk=entry.pk).values().get(), before)

    def test_contra_flag_locked_by_entries(self):  # AC-06
        account = self.create(self.client_a, 'Depreciación', '121005').data
        url = f'{ACCOUNTS}{account["id"]}/'
        self.assertTrue(self.client_a.patch(url, {'is_contra': True}, format='json').data['is_contra'])
        self.add_entry(account['id'], self.company_a)
        blocked = self.client_a.patch(url, {'is_contra': False}, format='json')
        self.assertEqual((blocked.status_code, blocked.data['code']), (409, 'account_has_entries'))

    def test_change_class_without_entries_and_kind_consistency(self):  # INV-03/04
        account = self.create(self.client_a, 'Caja', '101', kind='CASH').data
        url = f'{ACCOUNTS}{account["id"]}/'
        no = self.client_a.patch(url, {'account_class': 'EXPENSE'}, format='json')
        self.assertEqual(no.status_code, 400)  # conserva kind → inconsistente
        self.assertIn('kind', no.data)
        self.assertEqual(AccountModel.objects.get(pk=account['id']).account_class, 'ASSET')
        payload = {'account_class': 'EXPENSE', 'kind': None}  # REV-01: null explícito quita el tipo
        released = self.client_a.patch(url, payload, format='json')
        self.assertEqual((released.status_code, released.data['account_class'], released.data['kind']), (200, 'EXPENSE', None))
        self.client_a.post('/api/accounting/account-classes/EXPENSE/disable/')
        other = self.create(self.client_a, 'Otra', '102').data
        disabled = self.client_a.patch(f'{ACCOUNTS}{other["id"]}/', {'account_class': 'EXPENSE'}, format='json')
        self.assertEqual(disabled.status_code, 400)
        self.assertIn('account_class', disabled.data)

    def test_recode_to_existing_code_is_rejected_and_null_means_no_change(self):  # AC-01
        self.create(self.client_a, 'Caja', '101')
        other = self.create(self.client_a, 'Banco', '102').data
        url = f'{ACCOUNTS}{other["id"]}/'
        dup = self.client_a.patch(url, {'code': '101'}, format='json')
        self.assertEqual(dup.status_code, 400)
        self.assertIn('code', dup.data)
        same = self.client_a.patch(url, {'account_class': None, 'code': None}, format='json')
        self.assertEqual((same.status_code, same.data['code'], same.data['account_class']), (200, '102', 'ASSET'))


class HasEntriesTests(ApiBase):
    def test_accounts_expose_whether_they_have_entries(self):  # UI-02, REV-02
        with_entries = self.create(self.client_a, 'Caja', '111001', kind='CASH').data
        free = self.create(self.client_a, 'Banco', '111002', kind='BANK').data
        self.assertFalse(with_entries['has_entries'])
        self.add_entry(with_entries['id'], self.company_a)
        flags = {a['id']: a['has_entries'] for a in self.client_a.get(ACCOUNTS).data}
        self.assertEqual(flags, {with_entries['id']: True, free['id']: False})
        self.assertTrue(self.client_a.get(f'{ACCOUNTS}{with_entries["id"]}/').data['has_entries'])
        self.assertTrue(self.client_a.patch(f'{ACCOUNTS}{with_entries["id"]}/', {'name': 'Caja 2'}, format='json').data['has_entries'])
        self.assertTrue(self.client_a.post(f'{ACCOUNTS}{with_entries["id"]}/deactivate/').data['has_entries'])
        self.assertFalse(self.client_a.get(f'{ACCOUNTS}{free["id"]}/').data['has_entries'])

    def test_listing_uses_a_constant_number_of_queries(self):  # sin N+1
        def queries():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.client_a.get(ACCOUNTS).status_code, 200)
            return len(ctx)

        first = self.create(self.client_a, 'Cuenta 0', '500000').data
        self.add_entry(first['id'], self.company_a)
        one_account = queries()
        for n in range(1, 7):
            account = self.create(self.client_a, f'Cuenta {n}', str(500000 + n)).data
            self.add_entry(account['id'], self.company_a)
        self.assertEqual(queries(), one_account)


class KindClearingTests(ApiBase):
    def test_explicit_null_clears_the_money_type_and_absent_keeps_it(self):  # REV-01
        account = self.create(self.client_a, 'Caja', '101', kind='CASH').data
        url = f'{ACCOUNTS}{account["id"]}/'
        self.assertEqual(self.client_a.patch(url, {'name': 'Caja 2'}, format='json').data['kind'], 'CASH')
        cleared = self.client_a.patch(url, {'kind': None}, format='json')
        self.assertEqual((cleared.status_code, cleared.data['kind']), (200, None))
        self.assertIsNone(AccountModel.objects.get(pk=account['id']).kind)

    def test_legacy_money_account_can_be_reclassified_outside_asset(self):
        legacy = AccountModel.objects.create(company_id=self.company_a.id, name='Vieja', currency='BOB', kind='BANK')
        url = f'{ACCOUNTS}{legacy.id}/'
        stuck = self.client_a.patch(url, {'code': '5001', 'account_class': 'EXPENSE'}, format='json')
        self.assertEqual(stuck.status_code, 400)
        self.assertIn('kind', stuck.data)
        done = self.client_a.patch(url, {'code': '5001', 'account_class': 'EXPENSE', 'kind': None}, format='json')
        self.assertEqual((done.status_code, done.data['account_class'], done.data['kind']), (200, 'EXPENSE', None))


class StateAndLegacyTests(ApiBase):
    def test_deactivated_account_stays_listed_with_history_and_is_not_usable(self):  # AC-03
        account = self.create(self.client_a, 'Caja', '101', kind='CASH').data
        self.add_entry(account['id'], self.company_a)
        before = services.account_balances(self.company_a.id)
        self.assertFalse(self.client_a.post(f'{ACCOUNTS}{account["id"]}/deactivate/').data['is_active'])
        self.assertEqual(len(self.client_a.get(ACCOUNTS).data), 1)
        self.assertEqual(self.client_a.get(ACCOUNTS, {'active': 'false'}).data[0]['id'], account['id'])
        self.assertEqual(services.account_balances(self.company_a.id), before)
        with self.assertRaises(AccountValidationError):
            services.validate_money_account(self.company_a.id, account['id'])

    def test_no_delete_routes(self):  # AC-07, INV-06
        account = self.create(self.client_a, 'Caja', '101').data
        self.assertEqual(self.client_a.delete(f'{ACCOUNTS}{account["id"]}/').status_code, 405)
        self.assertEqual(AccountModel.objects.count(), 1)

    def test_legacy_account_without_code_or_class_stays_operational_and_completable(self):  # AC-08
        legacy = AccountModel.objects.create(company_id=self.company_a.id, name='Vieja', currency='BOB', kind='BANK')
        listed = self.client_a.get(ACCOUNTS).data[0]
        self.assertEqual((listed['code'], listed['account_class']), (None, None))
        self.assertEqual(services.validate_money_account(self.company_a.id, legacy.id).name, 'Vieja')
        self.add_entry(legacy.id, self.company_a)
        done = self.client_a.patch(f'{ACCOUNTS}{legacy.id}/', {'code': '111002', 'account_class': 'ASSET'}, format='json')
        self.assertEqual((done.status_code, done.data['code'], done.data['account_class']), (200, '111002', 'ASSET'))

    def test_deactivating_an_account_used_by_a_method_is_still_blocked(self):  # AC-09, INV-07
        account = self.create(self.client_a, 'Banco', '102', kind='BANK').data
        self.client_a.put(f'{METHODS}QR/', {'account_id': account['id'], 'is_active': True}, format='json')
        blocked = self.client_a.post(f'{ACCOUNTS}{account["id"]}/deactivate/')
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.data['code'], 'account_in_use')
        self.assertIn('QR', blocked.data['methods'])
        self.assertTrue(AccountModel.objects.get(pk=account['id']).is_active)


class ListTests(ApiBase):
    def test_orders_by_code_filters_by_class_and_isolates_companies(self):  # AC-10
        self.create(self.client_a, 'Alquiler', '611002', 'EXPENSE')
        self.create(self.client_a, 'Caja', '111001', kind='CASH')
        self.create(self.client_a, 'Banco', '111002', kind='BANK')
        AccountModel.objects.create(company_id=self.company_a.id, name='Anterior', currency='BOB')
        self.create(self.client_b, 'Ajena', '111001')
        rows = self.client_a.get(ACCOUNTS).data
        self.assertEqual([r['code'] for r in rows], ['111001', '111002', '611002', None])
        self.assertEqual([r['code'] for r in self.client_a.get(ACCOUNTS, {'account_class': 'asset'}).data], ['111001', '111002'])
        self.assertEqual(self.client_a.get(ACCOUNTS, {'account_class': 'OTHER'}).status_code, 400)
        foreign = self.client_b.get(ACCOUNTS).data[0]
        self.assertEqual(self.client_a.get(f'{ACCOUNTS}{foreign["id"]}/').status_code, 404)
        self.assertEqual(self.client_a.patch(f'{ACCOUNTS}{foreign["id"]}/', {'name': 'x'}, format='json').status_code, 404)


BEFORE = [('accounting', '0007_account_class')]
AFTER = [('accounting', '0008_account_code_contra')]


class MigrationTests(TransactionTestCase):
    def migrate(self, targets):
        MigrationExecutor(connection).migrate(targets)
        return MigrationExecutor(connection).loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_0008_keeps_existing_accounts_and_is_reversible(self):  # AC-11
        old = self.migrate(BEFORE)
        company = uuid4()
        account = old.get_model('accounting', 'AccountModel').objects.create(
            company_id=company, name='Banco', currency='BOB', kind='BANK', account_class='ASSET',
            opening_balance=Decimal('10.50'))
        new = self.migrate(AFTER)
        kept = new.get_model('accounting', 'AccountModel').objects.get(pk=account.pk)
        self.assertEqual((kept.name, kept.kind, kept.account_class, kept.code, kept.is_contra, kept.opening_balance),
                         ('Banco', 'BANK', 'ASSET', None, False, Decimal('10.50')))
        model = new.get_model('accounting', 'AccountModel')
        model.objects.create(company_id=company, name='A', currency='BOB')  # varias cuentas sin código conviven
        model.objects.create(company_id=company, name='B', currency='BOB')
        back = self.migrate(BEFORE)
        self.assertEqual(back.get_model('accounting', 'AccountModel').objects.get(pk=account.pk).name, 'Banco')
