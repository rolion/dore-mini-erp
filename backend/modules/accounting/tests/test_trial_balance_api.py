"""CONT-04: API de sumas y saldos (AC-01..06, INV-02..05)."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import transaction

from modules.accounting import services
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounting.tests.journal_support import make_account, make_period
from modules.accounting.tests.test_api import AccountingApiBase
from modules.accounting.tests.test_entries_api import enable

URL = '/api/accounting/balances/'


class BalanceApiTests(AccountingApiBase):
    def setUp(self):
        super().setUp()
        enable(self.company_a, 'accounting')
        enable(self.company_b, 'accounting')
        self.cash = make_account(self.company_a.id, 'Caja', code='111001')
        self.bank = make_account(self.company_a.id, 'Banco', code='111002')
        self.income = make_account(self.company_a.id, 'Ingresos', 'INCOME', code='411001')
        self.idle = make_account(self.company_a.id, 'Sin uso', 'EXPENSE', code='511001')
        self.old = make_account(self.company_a.id, 'Caja vieja', code='111003')
        self.period = make_period(self.company_a.id, 'Q4', date(2026, 10, 1), date(2026, 12, 31))
        make_period(self.company_a.id, 'Q3', date(2026, 7, 1), date(2026, 9, 30))

    def post(self, debit, credit, amount, day):
        with transaction.atomic():
            return services.post_journal_entry(self.company_a.id, services.JournalEntryInput(
                accounting_date=day, description='Mov', lines=[
                    services.JournalLineInput(debit.id, debit=Decimal(amount)),
                    services.JournalLineInput(credit.id, credit=Decimal(amount))])).entry

    def rows(self, **params):
        response = self.client_a.get(URL, params)
        self.assertEqual(response.status_code, 200, response.data)
        return {r['name']: r for r in response.data['rows']}, response.data

    def seed(self):
        self.post(self.cash, self.income, '1000.00', date(2026, 11, 5))
        return self.post(self.income, self.cash, '300.00', date(2026, 11, 20))

    def test_balances_by_difference_for_every_class(self):  # AC-01
        self.seed()
        rows, _ = self.rows()
        self.assertEqual((rows['Caja']['debit'], rows['Caja']['credit'], rows['Caja']['debit_balance'],
                          rows['Caja']['credit_balance']), ('1000.00', '300.00', '700.00', '0.00'))
        self.assertEqual((rows['Ingresos']['debit_balance'], rows['Ingresos']['credit_balance']), ('0.00', '700.00'))

    def test_idle_and_disabled_accounts_are_listed_with_zero(self):  # AC-03
        self.seed()
        self.old.deactivate()
        DjangoAccountRepository(self.company_a.id).save(self.old)
        rows, _ = self.rows()
        self.assertEqual(len(rows), 5)
        for name in ('Sin uso', 'Caja vieja'):
            self.assertEqual((rows[name]['debit'], rows[name]['debit_balance'], rows[name]['credit_balance']),
                             ('0.00', '0.00', '0.00'))
        self.assertFalse(rows['Caja vieja']['is_active'])

    def test_disabled_account_keeps_its_balance(self):  # AC-03
        self.post(self.old, self.income, '40.00', date(2026, 11, 5))
        self.old.deactivate()
        DjangoAccountRepository(self.company_a.id).save(self.old)
        rows, _ = self.rows()
        self.assertEqual(rows['Caja vieja']['debit_balance'], '40.00')

    def test_global_totals_balance_and_filters_narrow_them(self):  # AC-04
        self.seed()
        _, data = self.rows()
        self.assertTrue(data['totals']['balanced'])
        self.assertEqual(data['totals']['debit'], data['totals']['credit'])
        rows, data = self.rows(account_class='ASSET')
        self.assertEqual(set(rows), {'Caja', 'Banco', 'Caja vieja'})
        self.assertFalse(data['totals']['balanced'])
        rows, _ = self.rows(account_id=str(self.cash.id))
        self.assertEqual(set(rows), {'Caja'})

    def test_reversal_counts_on_its_own_date(self):  # AC-02
        original = self.seed()
        with transaction.atomic():
            services.reverse_journal_entry(self.company_a.id, original.id, date(2026, 12, 3), 'Error')
        november, _ = self.rows(date_from='2026-11-01', date_to='2026-11-30')
        self.assertEqual((november['Caja']['debit'], november['Caja']['credit']), ('1000.00', '300.00'))
        december, _ = self.rows(date_from='2026-12-01', date_to='2026-12-31')
        self.assertEqual((december['Caja']['opening_debit_balance'], december['Caja']['debit'],
                          december['Caja']['credit'], december['Caja']['debit_balance']),
                         ('700.00', '300.00', '0.00', '1000.00'))

    def test_range_gives_opening_range_and_closing(self):  # AC-05
        self.seed()
        rows, data = self.rows(date_from='2026-11-10')
        self.assertTrue(data['has_opening'])
        cash = rows['Caja']
        self.assertEqual((cash['opening_debit_balance'], cash['debit'], cash['credit'], cash['debit_balance']),
                         ('1000.00', '0.00', '300.00', '700.00'))

    def test_period_is_a_range_and_cannot_mix_with_dates(self):  # AC-06
        self.seed()
        rows, data = self.rows(period_id=str(self.period.id))
        self.assertEqual((data['date_from'], data['date_to']), (date(2026, 10, 1), date(2026, 12, 31)))
        self.assertEqual(rows['Caja']['debit'], '1000.00')
        self.assertEqual(self.client_a.get(URL, {'period_id': str(self.period.id), 'date_from': '2026-11-01'})
                         .status_code, 400)

    def test_invalid_filters_are_rejected(self):
        for params in ({'date_from': '2026-12-01', 'date_to': '2026-11-01'}, {'account_class': 'X'},
                       {'account_id': str(uuid4())}, {'period_id': str(uuid4())}, {'date_from': 'mal'}):
            self.assertEqual(self.client_a.get(URL, params).status_code, 400, params)

    def test_other_company_sees_nothing_of_this_one(self):  # INV-05
        self.seed()
        self.assertEqual(self.client_b.get(URL).data['rows'], [])
        self.assertEqual(self.client_b.get(URL, {'account_id': str(self.cash.id)}).status_code, 400)
