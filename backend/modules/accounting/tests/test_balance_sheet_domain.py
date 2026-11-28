"""Balance general: dominio y caso de uso sin BD (INV-01..06, AC-01, AC-03..06)."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from uuid import uuid4

from modules.accounting.application.balance_sheet import BalanceSheetFilters, GetBalanceSheet
from modules.accounting.domain.account import AccountValidationError
from modules.accounting.domain.balance_sheet import build_balance_sheet
from modules.accounting.domain.trial_balance import AccountMovements

D = Decimal


def account(name, account_class, code=None):
    return SimpleNamespace(id=uuid4(), name=name, account_class=account_class, code=code, is_active=True)


def mv(opening_debit='0', opening_credit='0', debit='0', credit='0'):
    return AccountMovements(D(opening_debit), D(opening_credit), D(debit), D(credit))


class Fixture:
    def __init__(self):
        self.cash = account('Caja', 'ASSET', '111')
        self.loan = account('Préstamo', 'LIABILITY', '211')
        self.capital = account('Capital', 'EQUITY', '311')
        self.sales = account('Ventas', 'INCOME', '411')
        self.rent = account('Alquiler', 'EXPENSE', '511')
        self.cost = account('Costo', 'COST', '611')
        self.accounts = [self.cash, self.loan, self.capital, self.sales, self.rent, self.cost]


class BalanceSheetDomainTests(TestCase):
    def setUp(self):
        self.f = Fixture()

    def test_natures_and_subtotals(self):  # INV-01, AC-01
        f = self.f
        sheet = build_balance_sheet(f.accounts, {
            f.cash.id: mv(debit='1500'), f.loan.id: mv(credit='500'), f.capital.id: mv(credit='1000')})
        assets, liabilities, equity = sheet.sections
        self.assertEqual(assets.rows[0].amounts.closing, D('1500'))
        self.assertEqual(liabilities.total.closing, D('500'))
        self.assertEqual(equity.total.closing, D('1000'))
        self.assertTrue(sheet.totals.balanced)

    def test_contra_balance_is_negative_and_subtracts(self):  # INV-01
        f = self.f
        bad = account('Depreciación', 'ASSET', '112')
        sheet = build_balance_sheet(f.accounts + [bad], {f.cash.id: mv(debit='1000'), bad.id: mv(credit='200')})
        self.assertEqual([r.amounts.closing for r in sheet.sections[0].rows], [D('1000'), D('-200')])
        self.assertEqual(sheet.totals.assets, D('800'))

    def test_opening_plus_movement_is_closing(self):  # INV-02, AC-03
        f = self.f
        sheet = build_balance_sheet(f.accounts, {f.cash.id: mv(opening_debit='100', debit='50', credit='20')})
        amounts = sheet.sections[0].rows[0].amounts
        self.assertEqual((amounts.opening, amounts.movement, amounts.closing), (D('100'), D('30'), D('130')))

    def test_results_go_to_equity_and_balance_with_range(self):  # INV-03, INV-04, AC-04
        f = self.f
        # antes del rango: venta 1000 (caja/ventas) y gasto 300; en el rango: venta 400, costo 100
        movements = {
            f.cash.id: mv(opening_debit='700', debit='300'),
            f.sales.id: mv(opening_credit='1000', credit='400'),
            f.rent.id: mv(opening_debit='300'),
            f.cost.id: mv(debit='100'),
        }
        sheet = build_balance_sheet(f.accounts, movements)
        equity = sheet.sections[2]
        self.assertEqual(equity.previous_result.opening, D('700'))
        self.assertEqual(equity.period_result.movement, D('300'))
        self.assertEqual(sheet.totals.equity, D('1000'))
        self.assertEqual(sheet.totals.assets, D('1000'))
        self.assertTrue(sheet.totals.balanced)

    def test_unclassified_with_balance_breaks_balance(self):  # INV-05, AC-05
        f = self.f
        loose = account('Vieja', None)
        sheet = build_balance_sheet(f.accounts + [loose], {f.cash.id: mv(debit='100'), loose.id: mv(credit='100')})
        self.assertEqual(sheet.totals.unclassified_balance, D('-100'))
        self.assertFalse(sheet.totals.balanced)
        quiet = build_balance_sheet(f.accounts + [loose], {f.cash.id: mv(debit='100'), f.capital.id: mv(credit='100')})
        self.assertTrue(quiet.totals.balanced)

    def test_zero_accounts_are_omitted_and_empty_ledger_balances(self):  # INV-06
        sheet = build_balance_sheet(self.f.accounts, {})
        self.assertTrue(all(not s.rows for s in sheet.sections))
        self.assertTrue(sheet.totals.balanced)

    def test_rows_sorted_by_code(self):
        f = self.f
        later = account('Banco', 'ASSET', '112')
        sheet = build_balance_sheet([later, f.cash], {later.id: mv(debit='1'), f.cash.id: mv(debit='1')})
        self.assertEqual([r.code for r in sheet.sections[0].rows], ['111', '112'])


class FakeJournal:
    def __init__(self, movements):
        self.movements, self.calls = movements, []

    def movements_by_account(self, date_from, date_to):
        self.calls.append((date_from, date_to))
        return self.movements


class FakeAccounts:
    def __init__(self, accounts):
        self.accounts = accounts

    def list(self, is_active=None, account_class=None):
        return self.accounts


class GetBalanceSheetTests(TestCase):
    def test_passes_range_to_journal(self):  # AC-02, AC-03
        f = Fixture()
        journal = FakeJournal({f.cash.id: mv(debit='10'), f.capital.id: mv(credit='10')})
        report = GetBalanceSheet(FakeAccounts(f.accounts), journal).execute(
            BalanceSheetFilters(date(2026, 1, 1), date(2026, 3, 31)))
        self.assertEqual(journal.calls, [(date(2026, 1, 1), date(2026, 3, 31))])
        self.assertTrue(report.sheet.totals.balanced)

    def test_inverted_range_is_rejected(self):  # AC-06
        with self.assertRaises(AccountValidationError) as ctx:
            GetBalanceSheet(FakeAccounts([]), FakeJournal({})).execute(
                BalanceSheetFilters(date(2026, 5, 1), date(2026, 4, 1)))
        self.assertIn('date_from', ctx.exception.errors)

    def test_same_day_is_valid(self):
        day = date(2026, 5, 1)
        GetBalanceSheet(FakeAccounts([]), FakeJournal({})).execute(BalanceSheetFilters(day, day))
