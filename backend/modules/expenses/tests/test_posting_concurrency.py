"""GAS-01 (REV-01): dos envíos simultáneos con la misma clave crean un solo gasto y un solo asiento (AC-04, INV-04)."""
from datetime import timedelta
from uuid import uuid4

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
from modules.expenses.application.commands import CreateExpense
from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.infrastructure.adapters import AccountingPosting
from modules.expenses.infrastructure.django.models import ExpenseModel
from modules.expenses.infrastructure.django.repositories import DjangoExpenseCategoryRepository, DjangoExpenseRepository

TODAY = timezone.localdate()


class ConcurrentExpenseTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('A')
        enable(self.company, 'accounting', 'expenses')
        accounts = DjangoAccountRepository(self.company.id)
        banco = money_account(accounts, 'Banco', '110102')
        gasto = make_account(self.company.id, 'Alquiler', 'EXPENSE', '510001')
        make_period(self.company.id, 'Año', TODAY - timedelta(days=200), TODAY + timedelta(days=100))
        self.category = DjangoExpenseCategoryRepository(self.company.id).save(ExpenseCategory.create('Alquiler'))
        accounting.set_category_account(self.company.id, self.category.id, gasto.id)
        with transaction.atomic():
            ConfigureMethod(accounts, DjangoMethodMappingRepository(self.company.id)).execute(
                'BANK_TRANSFER', banco.id, True)

    def create(self, key, results):  # `_run_together` ya abre la transacción de cada hilo
        case = CreateExpense(DjangoExpenseRepository(self.company.id), DjangoExpenseCategoryRepository(self.company.id),
                             posting=AccountingPosting(self.company.id))
        expense = case.execute(description='Alquiler', amount='500.00', category_id=self.category.id,
                               expense_date=TODAY, payment_method='BANK_TRANSFER', idempotency_key=key)
        results.append((expense.id, case.replayed))

    def test_two_simultaneous_submissions_with_the_same_key_create_one_expense_and_one_entry(self):  # AC-04
        key, results = uuid4(), []
        outcomes = _run_together(*[lambda: self.create(key, results)] * 2)
        self.assertEqual(outcomes, [None, None])
        self.assertEqual(len({expense_id for expense_id, _ in results}), 1)
        self.assertEqual(sorted(replayed for _, replayed in results), [False, True])
        self.assertEqual(ExpenseModel.objects.filter(company_id=self.company.id).count(), 1)
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 1)
