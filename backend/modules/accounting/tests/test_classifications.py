"""CONT-01: tipo de cuenta, clasificaciones por empresa y fachada de validación (AC-01..07; INV-02..05)."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient, APITestCase

from modules.accounting import services
from modules.accounting.domain.account import Account, AccountValidationError
from modules.accounting.domain.classification import Classification
from modules.accounting.infrastructure.django.models import AccountModel, ClassificationModel, EntryModel
from modules.accounting.infrastructure.django.repositories import (
    DjangoAccountRepository,
    DjangoClassificationRepository,
)
from modules.accounts.testing import authenticate, make_admin, make_company

ACCOUNTS = '/api/accounting/accounts/'
CLASSIFICATIONS = '/api/accounting/classifications/'


class DomainTests(SimpleTestCase):
    def test_account_kind_is_validated_and_optional_for_legacy(self):  # INV-02, AC-05
        self.assertEqual(Account.create('Banco', 'BOB', 'bank').kind, 'BANK')
        self.assertIsNone(Account.create('Vieja', 'BOB').kind)
        with self.assertRaises(AccountValidationError) as raised:
            Account.create('X', 'BOB', 'CHEQUERA')
        self.assertIn('kind', raised.exception.errors)

    def test_classification_rules(self):  # INV-03, INV-04
        c = Classification.create('  Alquiler ', 'expense')
        self.assertEqual((c.name, c.direction, c.is_active), ('Alquiler', 'EXPENSE', True))
        for bad_name in ('', None, 'x' * 81):
            with self.assertRaises(AccountValidationError):
                Classification.create(bad_name, 'INCOME')
        with self.assertRaises(AccountValidationError) as raised:
            Classification.create('Ventas', 'OTHER')
        self.assertIn('direction', raised.exception.errors)

    def test_usable_only_if_active_and_same_direction(self):  # INV-05
        c = Classification.create('Ventas', 'INCOME')
        c.ensure_usable('INCOME')
        with self.assertRaises(AccountValidationError):
            c.ensure_usable('EXPENSE')
        c.deactivate()
        with self.assertRaises(AccountValidationError):
            c.ensure_usable('INCOME')


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

    def create_classification(self, client, name, direction):
        response = client.post(CLASSIFICATIONS, {'name': name, 'direction': direction}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data


class AccountKindApiTests(ApiBase):
    def test_kind_required_on_create_and_editable(self):  # AC-05
        self.assertEqual(self.client_a.post(ACCOUNTS, {'name': 'Caja', 'currency': 'BOB'}, format='json').status_code, 400)
        bad = self.client_a.post(ACCOUNTS, {'name': 'Caja', 'currency': 'BOB', 'kind': 'X'}, format='json')
        self.assertEqual(bad.status_code, 400)
        created = self.client_a.post(ACCOUNTS, {'name': 'Caja', 'currency': 'BOB', 'kind': 'CASH'}, format='json')
        self.assertEqual((created.status_code, created.data['kind']), (201, 'CASH'))
        patched = self.client_a.patch(f'{ACCOUNTS}{created.data["id"]}/', {'kind': 'WALLET'}, format='json')
        self.assertEqual(patched.data['kind'], 'WALLET')

    def test_legacy_account_without_kind_is_listed_and_editable(self):  # AC-05
        legacy = AccountModel.objects.create(company_id=self.company_a.id, name='Vieja', currency='BOB')
        self.assertEqual(self.client_a.get(ACCOUNTS).data[0]['kind'], None)
        response = self.client_a.patch(f'{ACCOUNTS}{legacy.id}/', {'name': 'Vieja 2'}, format='json')
        self.assertEqual((response.status_code, response.data['kind']), (200, None))


class ClassificationApiTests(ApiBase):
    def test_crud_filters_and_duplicates(self):  # AC-06
        ventas = self.create_classification(self.client_a, 'Ventas', 'INCOME')
        self.create_classification(self.client_a, 'Alquiler', 'EXPENSE')
        # mismo nombre en la otra dirección sí; duplicado en la misma no
        self.create_classification(self.client_a, 'ventas', 'EXPENSE')
        dup = self.client_a.post(CLASSIFICATIONS, {'name': 'VENTAS', 'direction': 'INCOME'}, format='json')
        self.assertEqual(dup.status_code, 400)
        self.assertIn('name', dup.data)
        income = self.client_a.get(CLASSIFICATIONS, {'direction': 'INCOME'}).data
        self.assertEqual([c['name'] for c in income], ['Ventas'])
        self.assertEqual(self.client_a.get(CLASSIFICATIONS, {'direction': 'X'}).status_code, 400)
        renamed = self.client_a.patch(f'{CLASSIFICATIONS}{ventas["id"]}/', {'name': 'Ventas web'}, format='json')
        self.assertEqual(renamed.data['name'], 'Ventas web')

    def test_direction_cannot_change(self):  # INV-04, EDGE-03
        c = self.create_classification(self.client_a, 'Ventas', 'INCOME')
        response = self.client_a.patch(f'{CLASSIFICATIONS}{c["id"]}/', {'name': 'Ventas', 'direction': 'EXPENSE'},
                                       format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ClassificationModel.objects.get(pk=c['id']).direction, 'INCOME')

    def test_foreign_company_classification_is_rejected(self):  # AC-02
        c = self.create_classification(self.client_b, 'Ventas', 'INCOME')
        url = f'{CLASSIFICATIONS}{c["id"]}/'
        self.assertEqual(self.client_a.get(url).status_code, 404)
        self.assertEqual(self.client_a.patch(url, {'name': 'x'}, format='json').status_code, 404)
        self.assertEqual(self.client_a.post(f'{url}deactivate/').status_code, 404)
        self.assertEqual(self.client_a.post(f'{url}activate/').status_code, 404)
        self.assertEqual(self.client_a.get(CLASSIFICATIONS).data, [])

    def test_deactivate_and_activate(self):  # AC-03
        c = self.create_classification(self.client_a, 'Ventas', 'INCOME')
        self.assertFalse(self.client_a.post(f'{CLASSIFICATIONS}{c["id"]}/deactivate/').data['is_active'])
        self.assertEqual(self.client_a.get(CLASSIFICATIONS, {'active': 'true'}).data, [])
        self.assertEqual(len(self.client_a.get(CLASSIFICATIONS, {'active': 'false'}).data), 1)
        self.assertTrue(self.client_a.post(f'{CLASSIFICATIONS}{c["id"]}/activate/').data['is_active'])

    def test_requires_authentication(self):
        self.assertIn(APIClient().get(CLASSIFICATIONS).status_code, (401, 403))

    def test_contract_keeps_account_method_and_classification_apart(self):  # AC-07
        account = self.client_a.post(ACCOUNTS, {'name': 'Banco', 'currency': 'BOB', 'kind': 'BANK'}, format='json').data
        c = self.create_classification(self.client_a, 'Ventas', 'INCOME')
        self.assertNotIn('direction', account)
        self.assertNotIn('kind', c)
        self.assertNotIn('method', c)


class FacadeTests(TestCase):
    def setUp(self):
        self.a, self.b = make_company('A'), make_company('B')
        self.accounts = DjangoAccountRepository(self.a.id)
        self.classifications = DjangoClassificationRepository(self.a.id)

    def test_same_bank_account_serves_a_collection_and_a_payment(self):  # AC-01
        banco = self.accounts.save(Account.create('Banco', 'BOB', 'BANK'))
        with transaction.atomic():  # uso de cobro
            collected = services.record_entry(self.a.id, services.EntryInput(
                account_id=banco.id, currency='BOB', amount=Decimal('50.00'), payment_date=date(2026, 11, 1),
                method='BANK_TRANSFER', origin_kind='PRODUCT', origin_id=uuid4()))
        paid = services.validate_money_account(self.a.id, banco.id)  # uso de pago: sin restricción de dirección
        self.assertEqual((collected.entry.account_id, paid.account_id), (banco.id, banco.id))

    def test_account_from_another_company_or_inactive_is_rejected(self):  # AC-02, AC-03
        foreign = DjangoAccountRepository(self.b.id).save(Account.create('Ajena', 'BOB', 'BANK'))
        with self.assertRaises(AccountValidationError):
            services.validate_money_account(self.a.id, foreign.id)
        own = self.accounts.save(Account.create('Caja', 'BOB', 'CASH'))
        own.deactivate()
        self.accounts.save(own)
        with self.assertRaises(AccountValidationError):
            services.validate_money_account(self.a.id, own.id)

    def test_classification_validation(self):  # AC-02, AC-03
        income = self.classifications.save(Classification.create('Ventas', 'INCOME'))
        self.assertEqual(services.validate_classification(self.a.id, income.id, 'INCOME').direction, 'INCOME')
        with self.assertRaises(AccountValidationError):
            services.validate_classification(self.a.id, income.id, 'EXPENSE')
        with self.assertRaises(AccountValidationError):
            services.validate_classification(self.b.id, income.id, 'INCOME')
        income.deactivate()
        self.classifications.save(income)
        with self.assertRaises(AccountValidationError):
            services.validate_classification(self.a.id, income.id, 'INCOME')

    def test_deactivating_an_account_keeps_its_entries(self):  # AC-03, AC-04
        banco = self.accounts.save(Account.create('Banco', 'BOB', 'BANK'))
        origin = uuid4()
        with transaction.atomic():
            services.record_entry(self.a.id, services.EntryInput(
                account_id=banco.id, currency='BOB', amount=Decimal('50.00'), payment_date=date(2026, 11, 1),
                method='BANK_TRANSFER', origin_kind='PRODUCT', origin_id=origin))
        banco.deactivate()
        self.accounts.save(banco)
        row = EntryModel.objects.get(origin_id=origin)
        self.assertEqual((row.account_id, row.amount), (banco.id, Decimal('50.00')))
        with self.assertRaises(AccountValidationError):
            services.validate_money_account(self.a.id, banco.id)
