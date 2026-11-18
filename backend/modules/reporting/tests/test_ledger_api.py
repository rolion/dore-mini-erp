"""CONT-05: `GET /api/reports/ledger/` sobre el libro de asientos (AC-01..AC-06)."""
from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from modules.accounting import services
from modules.accounting.infrastructure.django.models import SettingsModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounting.tests.journal_support import make_account, make_period, money_account
from modules.accounts.testing import authenticate, make_admin, make_company
from modules.modularity.tests.test_enforcement import set_enabled
from modules.reporting.application.criteria import LEDGER_CRITERIA

URL = '/api/reports/ledger/'
RANGE = {'date_from': '2026-05-01', 'date_to': '2026-05-31'}


class LedgerReportApiTests(APITestCase):
    def setUp(self):
        self.company = make_company('A')
        self.other = make_company('B')
        authenticate(self.client, make_admin(self.company, username='ana'))
        set_enabled(self.company, ('reporting', 'accounting', 'sales', 'expenses', 'customers'))
        cid = self.company.id
        self.cash = money_account(DjangoAccountRepository(cid), 'Caja', '1101', kind='CASH')
        self.bank = money_account(DjangoAccountRepository(cid), 'Banco', '1102')
        self.income = make_account(cid, 'Ingresos', 'INCOME', '4101')
        make_period(cid)
        SettingsModel.objects.create(company_id=cid, cutoff_date=date(2026, 4, 1))

    def post(self, debit, credit, amount, on=date(2026, 5, 10)):
        services.post_journal_entry(self.company.id, services.JournalEntryInput(
            on, 'Asiento', [services.JournalLineInput(debit.id, debit=Decimal(amount)),
                            services.JournalLineInput(credit.id, credit=Decimal(amount))]))

    def test_ledger_report_returns_flow_result_coverage_and_criteria(self):  # AC-03, AC-05, API-01
        self.post(self.cash, self.income, '500.00')
        self.post(self.bank, self.cash, '200.00')
        response = self.client.get(URL, RANGE)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual((data['cash_flow']['inflow'], data['cash_flow']['outflow'], data['cash_flow']['net'],
                          data['cash_flow']['transfers']), ('500.00', '0.00', '500.00', '200.00'))
        self.assertEqual(data['result']['income'], '500.00')
        self.assertEqual(data['coverage'], {'cutoff_date': '2026-04-01', 'partial': False})
        self.assertEqual(data['criteria'], LEDGER_CRITERIA)
        self.assertEqual(data['period'], {'kind': 'range', **RANGE})

    def test_an_earlier_range_is_marked_partial(self):  # AC-05
        data = self.client.get(URL, {'date_from': '2026-03-01', 'date_to': '2026-05-31'}).json()
        self.assertTrue(data['coverage']['partial'])

    def test_the_report_only_counts_the_own_company(self):  # AC-04
        self.post(self.cash, self.income, '500.00')
        authenticate(self.client, make_admin(self.other, username='bea'))
        set_enabled(self.other, ('reporting', 'accounting'))
        data = self.client.get(URL, RANGE).json()
        self.assertEqual((data['cash_flow']['net'], data['result']['income'], data['cash_flow']['accounts']),
                         ('0.00', '0.00', []))

    def test_it_requires_the_accounting_module(self):  # AC-05
        set_enabled(self.company, ('reporting',))
        response = self.client.get(URL, RANGE)
        self.assertEqual((response.status_code, response.json()['module']), (403, 'accounting'))

    def test_an_invalid_period_is_rejected(self):
        self.assertEqual(self.client.get(URL, {'date_from': '2026-05-31', 'date_to': '2026-05-01'}).status_code, 400)
