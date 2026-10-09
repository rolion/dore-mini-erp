from datetime import date, datetime, timezone
from decimal import Decimal

from django.test import TestCase

from modules.expenses import services
from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.domain.expense import Expense
from modules.expenses.infrastructure.django.repositories import (
    DjangoExpenseCategoryRepository,
    DjangoExpenseRepository,
)


class ExpenseReportServiceTests(TestCase):
    def setUp(self):
        self.categories = DjangoExpenseCategoryRepository()
        self.expenses = DjangoExpenseRepository()

    def category(self, name, active=True):
        category = ExpenseCategory.create(name)
        category.active = active
        return self.categories.save(category)

    def expense(self, category, amount, on=date(2026, 10, 5), voided=False):
        expense = self.expenses.save(Expense.create('Gasto', amount, category.id, on))
        if voided:
            expense.void(datetime(2026, 10, 9, tzinfo=timezone.utc))
            self.expenses.save(expense)
        return expense

    def report(self, start=date(2026, 10, 1), end=date(2026, 10, 31)):
        return services.get_expense_report(start, end)

    def test_groups_by_category_and_total_is_the_sum_of_rows(self):  # AC-11, INV-07
        a, b = self.category('Materia prima'), self.category('Empaque')
        self.expense(a, '100.00')
        self.expense(a, '50.50')
        self.expense(b, '20.00')
        report = self.report()
        self.assertEqual([(r.name, r.total) for r in report.rows],
                         [('Materia prima', Decimal('150.50')), ('Empaque', Decimal('20.00'))])
        self.assertEqual(report.total, Decimal('170.50'))
        self.assertEqual(report.total, sum(r.total for r in report.rows))

    def test_excludes_voided_expenses(self):  # AC-11
        a = self.category('A')
        self.expense(a, '10.00')
        self.expense(a, '99.00', voided=True)
        self.assertEqual(self.report().total, Decimal('10.00'))

    def test_range_is_inclusive_and_ignores_other_dates(self):  # EDGE-02
        a = self.category('A')
        self.expense(a, '1.00', on=date(2026, 10, 1))
        self.expense(a, '2.00', on=date(2026, 10, 31))
        self.expense(a, '4.00', on=date(2026, 9, 30))
        self.expense(a, '8.00', on=date(2026, 11, 1))
        self.assertEqual(self.report().total, Decimal('3.00'))
        self.assertEqual(self.report(date(2026, 10, 31), date(2026, 10, 31)).total, Decimal('2.00'))

    def test_inactive_categories_with_expenses_still_appear(self):  # EDGE-08
        old = self.category('Vieja', active=False)
        self.category('Sin gastos')
        self.expense(old, '5.00')
        report = self.report()
        self.assertEqual([(r.name, r.active) for r in report.rows], [('Vieja', False)])

    def test_empty_period_is_zero_without_rows(self):  # EDGE-03
        report = self.report()
        self.assertEqual((report.total, report.rows), (Decimal('0.00'), ()))
