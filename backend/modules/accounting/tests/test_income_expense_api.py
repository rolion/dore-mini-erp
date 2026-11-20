"""Reporte de ingresos y egresos por mes: API (AC-01..08, API-01)."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from rest_framework.test import APIClient

from modules.accounting import services
from modules.accounting.tests.journal_support import make_account, make_period
from modules.accounting.tests.test_api import AccountingApiBase
from modules.accounting.tests.test_entries_api import enable

URL = '/api/accounting/income-expense/'


class IncomeExpenseApiTests(AccountingApiBase):
    def setUp(self):
        super().setUp()
        enable(self.company_a, 'accounting')
        enable(self.company_b, 'accounting')
        self.cash = make_account(self.company_a.id, 'Caja', code='111001')
        self.income = make_account(self.company_a.id, 'Ventas', 'INCOME', code='411001')
        self.expense = make_account(self.company_a.id, 'Alquiler', 'EXPENSE', code='511001')
        self.cost = make_account(self.company_a.id, 'Costo de ventas', 'COST', code='611001')
        self.period = make_period(self.company_a.id, '2026', date(2026, 1, 1), date(2026, 12, 31))

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
        self.post(self.cash, self.income, '1000.00', date(2026, 1, 10))
        self.post(self.expense, self.cash, '300.00', date(2026, 1, 15))
        self.post(self.cost, self.cash, '200.00', date(2026, 1, 20))
        return self.post(self.cash, self.income, '400.00', date(2026, 3, 5))

    def test_month_row_sums_income_expense_and_cost(self):  # AC-01
        self.seed()
        data = self.get(period_id=str(self.period.id))
        jan = data['months'][0]
        self.assertEqual((jan['month'], jan['income'], jan['expense'], jan['profit']),
                         ('2026-01', '1000.00', '500.00', '500.00'))
        self.assertEqual(data['period']['name'], '2026')

    def test_reversal_counts_on_its_own_date(self):  # AC-02
        entry = self.seed()
        with transaction.atomic():
            services.reverse_journal_entry(self.company_a.id, entry.id, date(2026, 4, 2), 'Error')
        months = {m['month']: m for m in self.get(period_id=str(self.period.id))['months']}
        self.assertEqual(months['2026-03']['income'], '400.00')
        self.assertEqual(months['2026-04']['income'], '-400.00')
        self.assertEqual(months['2026-01']['income'], '1000.00')

    def test_footer_totals_and_zero_months(self):  # AC-03, AC-07
        self.seed()
        data = self.get(period_id=str(self.period.id))
        self.assertEqual(len(data['months']), 12)
        self.assertEqual(data['months'][1]['income'], '0.00')
        self.assertEqual(data['totals'], {'income': '1400.00', 'expense': '500.00', 'profit': '900.00'})

    def test_default_period_when_no_params(self):  # AC-04
        make_period(self.company_a.id, 'Anterior', date(2024, 1, 1), date(2024, 12, 31))
        data = self.get()
        # el período de 2026 no contiene necesariamente hoy: se elige el abierto más reciente
        self.assertEqual(data['period']['id'], str(self.period.id))

    def test_months_filter_limits_rows_and_totals(self):  # AC-05
        self.seed()
        data = self.get(period_id=str(self.period.id), months='2026-03,2026-01')
        self.assertEqual([m['month'] for m in data['months']], ['2026-01', '2026-03'])
        self.assertEqual(data['totals']['income'], '1400.00')
        data = self.get(period_id=str(self.period.id), months='2026-03')
        self.assertEqual((len(data['months']), data['totals']['income']), (1, '400.00'))

    def test_invalid_inputs_are_400(self):
        for params in ({'period_id': '00000000-0000-0000-0000-000000000000'},
                       {'period_id': str(self.period.id), 'months': '2026-13'},
                       {'period_id': str(self.period.id), 'months': '2027-01'},
                       {'period_id': 'x'}):
            self.assertEqual(self.client_a.get(URL, params).status_code, 400, params)

    def test_no_periods_returns_empty_report(self):
        data = self.client_b.get(URL).data
        self.assertEqual((data['period'], data['months']), (None, []))
        self.assertEqual(data['totals']['profit'], '0.00')

    def test_other_company_data_and_periods_never_leak(self):  # AC-08
        self.seed()
        other = make_account(self.company_b.id, 'Ventas B', 'INCOME', code='411001')
        cash_b = make_account(self.company_b.id, 'Caja B', code='111001')
        self.post(cash_b, other, '9999.00', date(2026, 1, 12), company=self.company_b)
        data = self.get(period_id=str(self.period.id))
        self.assertEqual(data['months'][0]['income'], '1000.00')
        self.assertEqual(self.client_b.get(URL, {'period_id': str(self.period.id)}).status_code, 400)

    def test_requires_enabled_module_and_authentication(self):
        from modules.modularity.infrastructure.django.models import CompanyModuleModel
        CompanyModuleModel.objects.filter(company_id=self.company_a.id, module_key='accounting').delete()
        self.assertEqual(self.client_a.get(URL).status_code, 403)
        self.assertIn(APIClient().get(URL).status_code, (401, 403))
