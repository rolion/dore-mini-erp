"""PB-ACC-002: consulta del libro de entradas (AC-05..09)."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from modules.accounting import services
from modules.accounting.domain.account import Account
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounts.testing import authenticate, make_admin, make_company
from modules.modularity.infrastructure.django.models import CompanyModuleModel, CompanySettingsModel

ENTRIES = '/api/accounting/entries/'


def enable(company, *keys):
    CompanySettingsModel.objects.get_or_create(company_id=company.id)
    for key in keys:
        CompanyModuleModel.objects.get_or_create(company_id=company.id, module_key=key)


class EntriesApiBase(APITestCase):
    def setUp(self):
        self.company_a, self.company_b = make_company('A'), make_company('B')
        enable(self.company_a, 'accounting', 'sales', 'receivables')
        enable(self.company_b, 'accounting')
        self.client_a = self.login(make_admin(self.company_a, 'ana'))
        self.client_b = self.login(make_admin(self.company_b, 'beto'))
        self.caja = self.account(self.company_a, 'Caja', 'BOB')
        self.banco = self.account(self.company_a, 'Banco', 'BOB')
        self.dolares = self.account(self.company_a, 'Dólares', 'USD')

    @staticmethod
    def login(user):
        client = APIClient()
        authenticate(client, user)
        return client

    @staticmethod
    def account(company, name, currency):
        return DjangoAccountRepository(company.id).save(Account.create(name, currency))

    def record(self, company, account, amount, day, *, method='CASH', origin='PRODUCT', **extra):
        return services.record_entry(company.id, services.EntryInput(
            account_id=account.id, currency=account.currency, amount=Decimal(amount), payment_date=day,
            method=method, origin_kind=origin, origin_id=uuid4(), **extra))


class ListTests(EntriesApiBase):
    def seed(self, count=25):
        for index in range(count):
            self.record(self.company_a, self.caja, '10.00', date(2026, 11, 1 + index % 20))
        self.record(self.company_a, self.banco, '300.50', date(2026, 10, 5), method='QR', origin='SERVICE',
                    origin_document_ref='quotation/PRO-1', receipt_number='CB-000001')
        self.record(self.company_a, self.dolares, '70.00', date(2026, 11, 3), method='BANK_TRANSFER')
        self.record(self.company_b, self.account(self.company_b, 'Caja', 'BOB'), '999.00', date(2026, 11, 3))

    def test_totals_and_filters_cover_every_page(self):  # AC-05
        self.seed()
        first = self.client_a.get(ENTRIES, {'page_size': 10}).data
        self.assertEqual((first['count'], len(first['results'])), (27, 10))
        totals = {t['currency']: t for t in first['totals']}
        self.assertEqual(totals['BOB']['amount'], '550.50')
        self.assertEqual(totals['BOB']['count'], 26)
        self.assertEqual(totals['BOB']['by_origin'], {'PRODUCT': '250.00', 'SERVICE': '300.50'})
        self.assertEqual(totals['USD']['amount'], '70.00')
        self.assertEqual(totals['USD']['by_origin']['SERVICE'], '0.00')
        page_three = self.client_a.get(ENTRIES, {'page_size': 10, 'page': 3}).data
        self.assertEqual(page_three['totals'], first['totals'])  # los totales no dependen de la página

    def test_each_filter_narrows_both_rows_and_totals(self):  # AC-05
        self.seed()
        def query(**params):
            data = self.client_a.get(ENTRIES, params).data
            return data['count'], {t['currency']: t['amount'] for t in data['totals']}
        self.assertEqual(query(origin='SERVICE'), (1, {'BOB': '300.50'}))
        self.assertEqual(query(method='QR'), (1, {'BOB': '300.50'}))
        self.assertEqual(query(account_id=str(self.dolares.id)), (1, {'USD': '70.00'}))
        self.assertEqual(query(date_from='2026-10-01', date_to='2026-10-31'), (1, {'BOB': '300.50'}))
        self.assertEqual(query(date_from='2026-11-03', date_to='2026-11-03'), (3, {'BOB': '20.00', 'USD': '70.00'}))
        self.assertEqual(query(origin='SERVICE', method='CASH'), (0, {}))

    def test_period_and_coverage_are_reported(self):  # AC-09
        self.seed(2)
        data = self.client_a.get(ENTRIES, {'date_from': '2026-11-01'}).data
        self.assertEqual(str(data['period']['date_from']), '2026-11-01')
        self.assertIsNone(data['period']['date_to'])
        self.assertEqual(str(data['coverage']['first_payment_date']), '2026-10-05')  # sin filtros
        self.assertEqual(str(data['coverage']['last_payment_date']), '2026-11-03')
        self.assertIsNotNone(data['coverage']['first_recorded_at'])

    def test_empty_book_returns_empty_totals_and_null_coverage(self):  # AC-09
        data = self.client_a.get(ENTRIES).data
        self.assertEqual((data['count'], data['results'], data['totals']), (0, [], []))
        self.assertEqual(data['coverage'], {'first_payment_date': None, 'last_payment_date': None,
                                            'first_recorded_at': None})

    def test_invalid_filters_are_rejected(self):  # EDGE-01, EDGE-02
        for params in ({'date_from': '2026-12-01', 'date_to': '2026-11-01'}, {'date_from': 'x'}, {'method': 'CHEQUE'},
                       {'origin': 'ORDER'}, {'account_id': 'no-uuid'}):
            self.assertEqual(self.client_a.get(ENTRIES, params).status_code, 400, params)

    def test_rows_show_origin_link_data_and_no_free_text(self):  # AC-08
        self.seed(0)
        row = next(r for r in self.client_a.get(ENTRIES).data['results'] if r['origin']['kind'] == 'SERVICE')
        self.assertEqual(row['source'], {'document_ref': 'quotation/PRO-1', 'receipt_number': 'CB-000001',
                                         'available': True})
        self.assertEqual((row['amount'], row['method_label'], row['origin']['label']), ('300.50', 'QR', 'Servicios'))
        self.assertEqual(row['account']['name'], 'Banco')
        self.assertNotIn('reference', row)

    def test_source_link_is_unavailable_when_the_origin_module_is_disabled(self):  # AC-07
        self.seed(0)
        CompanyModuleModel.objects.filter(company_id=self.company_a.id, module_key='receivables').delete()
        rows = {r['origin']['kind']: r for r in self.client_a.get(ENTRIES).data['results']}
        self.assertFalse(rows['SERVICE']['source']['available'])
        self.assertTrue(rows['PRODUCT']['source']['available'])


class DetailAndAccessTests(EntriesApiBase):
    def test_detail_returns_the_entry_and_hides_other_companies(self):  # AC-07
        mine = self.record(self.company_a, self.caja, '10.00', date(2026, 11, 1))
        theirs = self.record(self.company_b, self.account(self.company_b, 'Caja', 'BOB'), '5.00', date(2026, 11, 1))
        detail = self.client_a.get(f'{ENTRIES}{mine.entry_id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertIn('id', detail.data['source'])
        self.assertEqual(self.client_a.get(f'{ENTRIES}{theirs.entry_id}/').status_code, 404)
        self.assertEqual(self.client_a.get(f'{ENTRIES}{uuid4()}/').status_code, 404)

    def test_each_company_only_sees_its_own_entries(self):  # AC-07
        self.record(self.company_a, self.caja, '10.00', date(2026, 11, 1))
        self.record(self.company_b, self.account(self.company_b, 'Caja', 'BOB'), '5.00', date(2026, 11, 1))
        self.assertEqual(self.client_b.get(ENTRIES).data['totals'][0]['amount'], '5.00')
        # filtrar por una cuenta ajena no devuelve nada ajeno
        self.assertEqual(self.client_b.get(ENTRIES, {'account_id': str(self.caja.id)}).data['count'], 0)

    def test_non_admin_and_anonymous_users_are_rejected(self):  # AC-07
        self.assertIn(APIClient().get(ENTRIES).status_code, (401, 403))
        loner = APIClient()
        authenticate(loner, get_user_model().objects.create_user(username='solo', password='x-Pass-123'))
        self.assertEqual(loner.get(ENTRIES).status_code, 403)

    def test_accounting_disabled_blocks_the_book(self):  # AC-07
        CompanyModuleModel.objects.filter(company_id=self.company_a.id, module_key='accounting').delete()
        response = self.client_a.get(ENTRIES)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'module_disabled')

    def test_there_are_no_manual_write_endpoints(self):  # AC-08
        entry = self.record(self.company_a, self.caja, '10.00', date(2026, 11, 1))
        for url in (ENTRIES, f'{ENTRIES}{entry.entry_id}/'):
            for method in ('post', 'put', 'patch', 'delete'):
                self.assertEqual(getattr(self.client_a, method)(url, {}, format='json').status_code, 405,
                                 f'{method} {url}')

    def test_account_currency_cannot_change_once_it_has_entries(self):  # INV-08 vía API
        self.record(self.company_a, self.caja, '10.00', date(2026, 11, 1))
        response = self.client_a.patch(f'/api/accounting/accounts/{self.caja.id}/', {'currency': 'USD'}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'account_has_entries')
