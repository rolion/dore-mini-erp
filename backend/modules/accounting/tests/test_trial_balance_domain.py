"""CONT-04: dominio de sumas y saldos (AC-01, AC-05, INV-01, INV-06)."""
from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from uuid import uuid4

from modules.accounting.domain.trial_balance import AccountMovements, TrialBalanceRow, TrialBalanceTotals, split_balance

D = Decimal


def account(name='Caja'):
    return SimpleNamespace(id=uuid4(), code='111', name=name, account_class='ASSET', is_active=True)


class TrialBalanceDomainTests(TestCase):
    def test_debit_and_credit_balances_use_the_difference_only(self):  # AC-01 / INV-01
        self.assertEqual(split_balance(D('1000.00'), D('300.00')), (D('700.00'), D('0.00')))
        self.assertEqual(split_balance(D('0.00'), D('1000.00')), (D('0.00'), D('1000.00')))
        self.assertEqual(split_balance(D('50.00'), D('50.00')), (D('0.00'), D('0.00')))

    def test_account_without_movements_is_all_zero(self):  # AC-03
        row = TrialBalanceRow.build(account(), None)
        self.assertEqual((row.debit, row.credit, row.debit_balance, row.credit_balance), (D('0.00'),) * 4)

    def test_closing_balance_is_opening_plus_range(self):  # AC-05 / INV-02
        row = TrialBalanceRow.build(account(), AccountMovements(D('100.00'), D('400.00'), D('250.00'), D('50.00')))
        self.assertEqual((row.opening_debit_balance, row.opening_credit_balance), (D('0.00'), D('300.00')))
        self.assertEqual((row.debit, row.credit), (D('250.00'), D('50.00')))
        self.assertEqual((row.debit_balance, row.credit_balance), (D('0.00'), D('100.00')))

    def test_totals_add_rows_and_flag_balance(self):  # INV-06
        cash = TrialBalanceRow.build(account(), AccountMovements(debit=D('1000.00'), credit=D('300.00')))
        income = TrialBalanceRow.build(account('Ingresos'), AccountMovements(debit=D('300.00'), credit=D('1000.00')))
        self.assertTrue(TrialBalanceTotals.of([cash, income]).balanced)
        self.assertFalse(TrialBalanceTotals.of([cash]).balanced)
