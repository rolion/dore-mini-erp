"""GAS-02: al anular un gasto contabilizado se revierte el asiento completo (BD real, Contabilidad real)."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from modules.accounting import services as accounting
from modules.accounting.infrastructure.django.models import (
    AccountModel,
    FiscalPeriodModel,
    JournalEntryModel,
    SettingsModel,
)
from modules.accounting.tests.journal_support import make_period
from modules.accounts.testing import authenticate, make_admin
from modules.expenses.infrastructure.django.models import ExpenseModel
from modules.modularity.infrastructure.django.models import CompanyModuleModel

from .test_posting_api import CATEGORIES, EXPENSES, TODAY, PostingApiBase, enable


class VoidPostedExpenseTests(PostingApiBase):
    def void(self, expense, expected=200, client=None):
        response = (client or self.client).post(f'{EXPENSES}{expense["id"]}/void/')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def original(self, expense):
        return accounting.find_automatic_entry(self.company.id, 'EXPENSE_RECORD', expense['id'])

    def reversal(self, expense):
        return JournalEntryModel.objects.get(company_id=self.company.id, reverses_id=self.original(expense).id)

    def net(self, account):
        balance = accounting.journal_balances(self.company.id, [account.id]).get(account.id)
        return (balance.debit - balance.credit) if balance else Decimal('0')

    def test_voiding_reverses_every_line_with_the_original_accounts_and_neutralizes_balances(self):  # AC-01
        created = self.create(amount='200.00')
        original = self.original(created)
        body = self.void(created)
        reversal = accounting.get_journal_entry(self.company.id, self.reversal(created).id)
        self.assertEqual([(line.account_id, line.debit, line.credit) for line in reversal.lines],
                         [(self.alquiler.id, 0, Decimal('200.00')), (self.banco.id, Decimal('200.00'), 0)])
        self.assertEqual(reversal.reverses_id, original.id)
        self.assertEqual(self.original(created).lines, original.lines)  # el original no cambia
        self.assertEqual((self.net(self.alquiler), self.net(self.banco)), (0, 0))
        self.assertEqual((body['status'], body['journal_entry_id'], body['reversal_entry_id']),
                         ('VOIDED', str(original.id), str(reversal.id)))

    def test_the_reversal_records_who_when_and_why(self):  # AC-05
        created = self.create()
        self.void(created)
        reversal = self.reversal(created)
        self.assertEqual((reversal.created_by_name, reversal.accounting_date, reversal.reversal_reason),
                         ('ana', TODAY, 'Anulación de gasto'))
        self.assertEqual(reversal.created_by, get_user_model().objects.get(username='ana').pk)

    def test_the_detail_exposes_the_reversal_only_after_voiding(self):  # AC-07
        created = self.create()
        self.assertIsNone(self.client.get(f'{EXPENSES}{created["id"]}/').json()['reversal_entry_id'])
        self.void(created)
        detail = self.client.get(f'{EXPENSES}{created["id"]}/').json()
        self.assertEqual(detail['reversal_entry_id'], str(self.reversal(created).id))

    def test_the_reversal_keeps_the_original_accounts_after_config_changes_and_deactivation(self):  # AC-03
        created = self.create()
        accounting.set_category_account(self.company.id, self.category_id(), self.luz.id)
        self.map_method('BANK_TRANSFER', self.caja)
        AccountModel.objects.filter(pk__in=[self.alquiler.id, self.banco.id]).update(is_active=False)
        self.void(created)
        reversal = accounting.get_journal_entry(self.company.id, self.reversal(created).id)
        self.assertEqual({line.account_id for line in reversal.lines}, {self.alquiler.id, self.banco.id})
        self.assertEqual((self.net(self.alquiler), self.net(self.banco)), (0, 0))

    def test_a_closed_original_period_is_not_rewritten_and_the_reversal_goes_to_the_open_one(self):  # AC-04
        accounting.coverage_status(self.company.id, TODAY)  # crea el ajuste con corte = hoy
        SettingsModel.objects.filter(company_id=self.company.id).update(cutoff_date=TODAY - timedelta(days=200))
        FiscalPeriodModel.objects.filter(pk=self.period.id).update(end_date=TODAY - timedelta(days=10))
        make_period(self.company.id, 'Nuevo', TODAY - timedelta(days=9), TODAY + timedelta(days=100))
        created = self.create(expense_date=(TODAY - timedelta(days=20)).isoformat())
        FiscalPeriodModel.objects.filter(pk=self.period.id).update(status='CLOSED')
        self.void(created)
        reversal = self.reversal(created)
        self.assertEqual(reversal.accounting_date, TODAY)
        self.assertNotEqual(reversal.period_id, self.period.id)
        self.assertEqual(JournalEntryModel.objects.filter(period_id=self.period.id).count(), 1)  # solo el original

    def test_a_failed_reversal_leaves_the_expense_active_and_no_reversal(self):  # AC-02
        created = self.create()
        FiscalPeriodModel.objects.filter(pk=self.period.id).update(status='CLOSED')
        self.assertEqual(self.void(created, expected=409)['code'], 'fiscal_period_closed')
        self.assertEqual(ExpenseModel.objects.get(pk=created['id']).status, 'ACTIVE')
        self.assertFalse(JournalEntryModel.objects.filter(reverses_id__isnull=False).exists())

    def test_voiding_after_accounting_was_disabled_still_reverses_the_entry(self):  # AC-06
        created = self.create()
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='accounting').delete()
        self.void(created)
        self.assertEqual(JournalEntryModel.objects.filter(reverses_id=self.original(created).id).count(), 1)

    def test_an_expense_recorded_without_coverage_is_voided_without_a_reversal(self):  # AC-04
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='accounting').delete()
        created = self.create(expense_date=(TODAY - timedelta(days=3)).isoformat())
        self.assertFalse(created['posted'])
        enable(self.company, 'accounting')  # ahora con cobertura desde hoy: el gasto es anterior al corte
        self.void(created)
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 0)
        self.assertIsNone(self.client.get(f'{EXPENSES}{created["id"]}/').json()['reversal_entry_id'])

    def test_another_company_cannot_void_the_expense_and_nothing_is_reversed(self):  # AC-08
        created = self.create()
        enable(self.other, 'accounting', 'expenses')
        client = APIClient()
        authenticate(client, make_admin(self.other, username='beto'))
        self.void(created, expected=404, client=client)
        self.assertEqual(ExpenseModel.objects.get(pk=created['id']).status, 'ACTIVE')
        self.assertFalse(JournalEntryModel.objects.filter(reverses_id__isnull=False).exists())

    def test_voiding_twice_creates_a_single_reversal(self):  # EDGE-03
        created = self.create()
        self.void(created)
        self.assertEqual(self.client.post(f'{EXPENSES}{created["id"]}/void/').status_code, 409)
        self.assertEqual(JournalEntryModel.objects.filter(reverses_id__isnull=False).count(), 1)

    def category_id(self):
        from uuid import UUID
        return UUID(self.category['id'])


__all__ = ['CATEGORIES']
