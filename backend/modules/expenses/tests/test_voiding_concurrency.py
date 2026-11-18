"""GAS-02 (AC-02): dos anulaciones simultáneas del mismo gasto crean una sola reversión."""
from datetime import timedelta

from django.db import transaction
from django.test import TransactionTestCase
from django.utils import timezone

from modules.accounting import services as accounting
from modules.accounting.application.use_cases import ConfigureMethod
from modules.accounting.infrastructure.django.models import JournalEntryModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository, DjangoMethodMappingRepository
from modules.accounting.tests.journal_support import make_account, make_period, money_account
from modules.accounting.tests.test_concurrency import _run_together
from modules.accounting.tests.test_entries_api import enable
from modules.accounts.testing import make_company
from modules.expenses.application.commands import CreateExpense, VoidExpense
from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.domain.exceptions import ExpenseRuleViolation
from modules.expenses.infrastructure.adapters import AccountingPosting, SystemClock
from modules.expenses.infrastructure.django.models import ExpenseModel
from modules.expenses.infrastructure.django.repositories import DjangoExpenseCategoryRepository, DjangoExpenseRepository

TODAY = timezone.localdate()


class ConcurrentVoidTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('A')
        enable(self.company, 'accounting', 'expenses')
        accounts = DjangoAccountRepository(self.company.id)
        banco = money_account(accounts, 'Banco', '110102')
        gasto = make_account(self.company.id, 'Alquiler', 'EXPENSE', '510001')
        make_period(self.company.id, 'Año', TODAY - timedelta(days=200), TODAY + timedelta(days=100))
        category = DjangoExpenseCategoryRepository(self.company.id).save(ExpenseCategory.create('Alquiler'))
        accounting.set_category_account(self.company.id, category.id, gasto.id)
        with transaction.atomic():
            ConfigureMethod(accounts, DjangoMethodMappingRepository(self.company.id)).execute(
                'BANK_TRANSFER', banco.id, True)
            self.expense = CreateExpense(
                DjangoExpenseRepository(self.company.id), DjangoExpenseCategoryRepository(self.company.id),
                posting=AccountingPosting(self.company.id),
            ).execute(description='Alquiler', amount='200.00', category_id=category.id, expense_date=TODAY,
                      payment_method='BANK_TRANSFER')

    def void(self):  # `_run_together` ya abre la transacción de cada hilo
        VoidExpense(DjangoExpenseRepository(self.company.id), SystemClock(),
                    AccountingPosting(self.company.id)).execute(self.expense.id, 1, 'ana')

    def test_two_simultaneous_voids_create_one_reversal_and_one_succeeds(self):
        outcomes = _run_together(self.void, self.void)
        self.assertEqual(sum(outcome is None for outcome in outcomes), 1)
        self.assertTrue(all(isinstance(o, ExpenseRuleViolation) for o in outcomes if o is not None))
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id, reverses_id__isnull=False).count(), 1)
        self.assertEqual(ExpenseModel.objects.get(pk=self.expense.id).status, 'VOIDED')
