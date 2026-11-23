"""Reporte de ingresos y egresos por mes: dominio puro (INV-01..03, AC-03, AC-07)."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase

from modules.accounting.domain.income_expense import (
    IncomeExpenseTotals,
    build_months,
    default_period,
    month_keys,
)

D = Decimal


def period(start, end, is_open=True):
    return SimpleNamespace(start_date=start, end_date=end, is_open=is_open,
                           contains=lambda day: start <= day <= end)


class MonthKeysTests(TestCase):
    def test_partial_edge_months_and_more_than_twelve(self):  # INV-03
        self.assertEqual(month_keys(date(2026, 11, 15), date(2027, 1, 10)), ['2026-11', '2026-12', '2027-01'])
        self.assertEqual(len(month_keys(date(2026, 1, 1), date(2027, 6, 30))), 18)


class BuildMonthsTests(TestCase):
    def test_signs_by_class_and_profit(self):  # AC-01, INV-01
        months = build_months(['2026-01'], [
            ('2026-01', 'INCOME', D('0'), D('1000.00')), ('2026-01', 'EXPENSE', D('300.00'), D('0')),
            ('2026-01', 'COST', D('200.00'), D('0')), ('2026-01', 'ASSET', D('900.00'), D('0')),
            ('2026-01', None, D('5.00'), D('0'))])
        self.assertEqual((months[0].income, months[0].expense, months[0].profit),
                         (D('1000.00'), D('500.00'), D('500.00')))

    def test_corrective_entries_net_out(self):  # AC-02
        months = build_months(['2026-02'], [('2026-02', 'INCOME', D('300.00'), D('1000.00'))])
        self.assertEqual(months[0].income, D('700.00'))

    def test_empty_months_are_zero_and_outside_months_ignored(self):  # AC-07
        months = build_months(['2026-01', '2026-02'], [('2026-03', 'INCOME', D('0'), D('9.00'))])
        self.assertEqual([(m.income, m.expense, m.profit) for m in months], [(D('0.00'),) * 3] * 2)

    def test_totals_sum_the_rows(self):  # AC-03
        months = build_months(['2026-01', '2026-02'], [
            ('2026-01', 'INCOME', D('0'), D('100.00')), ('2026-02', 'INCOME', D('0'), D('50.00')),
            ('2026-02', 'EXPENSE', D('80.00'), D('0'))])
        totals = IncomeExpenseTotals.of(months)
        self.assertEqual((totals.income, totals.expense, totals.profit), (D('150.00'), D('80.00'), D('70.00')))


class DefaultPeriodTests(TestCase):
    def test_rules(self):  # INV-02
        today = date(2026, 11, 20)
        current = period(date(2026, 1, 1), date(2026, 12, 31))
        old = period(date(2025, 1, 1), date(2025, 12, 31))
        closed = period(date(2026, 1, 1), date(2026, 12, 31), is_open=False)
        later = period(date(2027, 1, 1), date(2027, 12, 31))
        self.assertIsNone(default_period([], today))
        self.assertIs(default_period([old, current], today), current)
        self.assertIs(default_period([closed, old], today), old)  # sin abierto que contenga hoy: abierto más reciente
        self.assertIs(default_period([old, later], today), later)
        self.assertIs(default_period([closed], today), closed)
