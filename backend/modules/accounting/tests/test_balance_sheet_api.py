"""Balance general: API (AC-01..07, API-01)."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from rest_framework.test import APIClient

from modules.accounting import services
from modules.accounting.infrastructure.django.models import AccountModel
from modules.accounting.tests.journal_support import make_account, make_period
from modules.accounting.tests.test_api import AccountingApiBase
from modules.accounting.tests.test_entries_api import enable

URL = '/api/accounting/balance-sheet/'


class BalanceSheetApiTests(AccountingApiBase):
    def setUp(self):
        super().setUp()
        enable(self.company_a, 'accounting')
        enable(self.company_b, 'accounting')
        cid = self.company_a.id
        self.cash = make_account(cid, 'Caja', code='111001')
        self.capital = make_account(cid, 'Capital', 'EQUITY', code='311001')
        self.income = make_account(cid, 'Ventas', 'INCOME', code='411001')
        self.expense = make_account(cid, 'Alquiler', 'EXPENSE', code='511001')
        # Todo asiento exige un período fiscal abierto que contenga su fecha contable.
        make_period(cid, '2026', date(2026, 1, 1), date(2026, 12, 31))
        make_period(self.company_b.id, '2026 B', date(2026, 1, 1), date(2026, 12, 31))

    def post(self, debit, credit, amount, day, company=None):
        with transaction.atomic():
            return services.post_journal_entry((company or self.company_a).id, services.JournalEntryInput(
                accounting_date=day, description='Mov', lines=[
                    services.JournalLineInput(debit.id, debit=Decimal(amount)),
                    services.JournalLineInput(credit.id, credit=Decimal(amount))])).entry

    def get(self, **params):
        response = self.client_a.get(URL, params)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def seed(self):
        self.post(self.cash, self.capital, '5000.00', date(2026, 1, 2))
        self.post(self.cash, self.income, '1000.00', date(2026, 1, 10))
        self.post(self.expense, self.cash, '300.00', date(2026, 2, 5))
        self.post(self.cash, self.income, '400.00', date(2026, 3, 5))

    def section(self, data, key):
        return next(s for s in data['sections'] if s['key'] == key)

    def test_sections_and_totals_whole_ledger(self):  # AC-01, AC-02, AC-04
        self.seed()
        data = self.get()
        self.assertEqual([s['key'] for s in data['sections']], ['ASSET', 'LIABILITY', 'EQUITY'])
        asset = self.section(data, 'ASSET')
        self.assertEqual((asset['rows'][0]['name'], asset['total']['closing']), ('Caja', '6100.00'))
        equity = self.section(data, 'EQUITY')
        self.assertEqual(equity['period_result']['closing'], '1100.00')
        self.assertEqual(equity['total']['closing'], '6100.00')
        self.assertEqual(data['totals']['balanced'], True)
        self.assertFalse(data['has_opening'])

    def test_date_to_is_cutoff(self):  # AC-02
        self.seed()
        data = self.get(date_to='2026-02-28')
        self.assertEqual(data['totals']['assets'], '5700.00')
        self.assertTrue(data['totals']['balanced'])

    def test_date_from_splits_opening_and_movement(self):  # AC-03, AC-04
        self.seed()
        data = self.get(date_from='2026-02-01', date_to='2026-12-31')
        self.assertTrue(data['has_opening'])
        cash = self.section(data, 'ASSET')['rows'][0]
        self.assertEqual((cash['opening'], cash['movement'], cash['closing']), ('6000.00', '100.00', '6100.00'))
        equity = self.section(data, 'EQUITY')
        self.assertEqual(equity['previous_result']['opening'], '1000.00')
        self.assertEqual(equity['period_result']['movement'], '100.00')
        self.assertTrue(data['totals']['balanced'])

    def test_unclassified_account_with_balance_is_reported(self):  # AC-05
        # Un asiento nuevo rechaza cuentas sin clasificar: se publica con una clasificada y luego se desclasifica
        # (caso de las cuentas antiguas con movimientos).
        loose = make_account(self.company_a.id, 'Vieja', 'LIABILITY', code='999001')
        self.post(self.cash, loose, '50.00', date(2026, 1, 2))
        AccountModel.objects.filter(id=loose.id).update(account_class=None)
        totals = self.get()['totals']
        self.assertEqual(totals['unclassified_balance'], '-50.00')
        self.assertFalse(totals['balanced'])

    def test_invalid_dates_are_400(self):  # AC-06
        for params in ({'date_from': '2026-05-01', 'date_to': '2026-04-01'}, {'date_from': 'x'}):
            self.assertEqual(self.client_a.get(URL, params).status_code, 400, params)

    def test_other_company_data_never_leaks(self):  # AC-07
        self.seed()
        cash_b = make_account(self.company_b.id, 'Caja B', code='111001')
        capital_b = make_account(self.company_b.id, 'Capital B', 'EQUITY', code='311001')
        self.post(cash_b, capital_b, '9999.00', date(2026, 1, 2), company=self.company_b)
        self.assertEqual(self.get()['totals']['assets'], '6100.00')

    def test_requires_enabled_module_and_authentication(self):  # AC-07
        from modules.modularity.infrastructure.django.models import CompanyModuleModel
        CompanyModuleModel.objects.filter(company_id=self.company_a.id, module_key='accounting').delete()
        self.assertEqual(self.client_a.get(URL).status_code, 403)
        self.assertIn(APIClient().get(URL).status_code, (401, 403))
