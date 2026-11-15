"""CONT-06: corte, cobertura, apertura, ciclo de vida del módulo e independencia de Gastos y Compras."""
import ast
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from modules.accounting import services
from modules.accounting.domain.account import Account, AccountValidationError, validate_opening_balance
from modules.accounting.domain.coverage import Gap, Period, coverage_status, gaps, validate_cutoff
from modules.accounting.infrastructure.django.models import (
    AccountModel,
    CoveragePeriodModel,
    EntryModel,
    SettingsModel,
)
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounts.testing import authenticate, make_admin, make_company
from modules.expenses.infrastructure.django.models import ExpenseModel
from modules.expenses.tests.test_api import ExpensesApiTestCase
from modules.purchases.tests.test_payment_api import PaymentApiTestCase

ENABLE = '/api/modules/accounting/enable/'
DISABLE = '/api/modules/accounting/disable/'
SETTINGS = '/api/accounting/settings/'
ACCOUNTS = '/api/accounting/accounts/'
TODAY = timezone.localdate()


class DomainTests(SimpleTestCase):
    def test_gaps_between_periods(self):  # INV-01
        periods = [Period(date(2026, 1, 1), date(2026, 2, 1)), Period(date(2026, 3, 1), date(2026, 3, 10)),
                   Period(date(2026, 3, 10), None)]
        self.assertEqual(gaps(periods), [Gap(date(2026, 2, 1), date(2026, 3, 1))])
        self.assertEqual(gaps([Period(date(2026, 1, 1))]), [])

    def test_coverage_status_reasons(self):  # AC-07, INV-04
        periods = [Period(date(2026, 1, 1), date(2026, 2, 1)), Period(date(2026, 3, 1), None)]
        kwargs = dict(cutoff_date=date(2026, 1, 1), periods=periods)
        self.assertTrue(coverage_status(enabled=True, effective_date=date(2026, 3, 5), **kwargs).covered)
        self.assertEqual(coverage_status(enabled=True, effective_date=date(2025, 12, 31), **kwargs).reason,
                         'before_cutoff')
        self.assertEqual(coverage_status(enabled=True, effective_date=date(2026, 2, 15), **kwargs).reason, 'in_gap')
        self.assertEqual(coverage_status(enabled=False, effective_date=date(2026, 3, 5), **kwargs).reason,
                         'accounting_disabled')
        self.assertEqual(coverage_status(enabled=True, cutoff_date=None, periods=[],
                                         effective_date=date(2026, 3, 5)).reason, 'accounting_disabled')

    def test_cutoff_cannot_be_future_or_invalid(self):  # EDGE-01
        today = date(2026, 11, 15)
        self.assertEqual(validate_cutoff(date(2026, 11, 15), today), today)
        for bad in (date(2026, 11, 16), '2026-11-01', None):
            with self.assertRaises(AccountValidationError) as raised:
                validate_cutoff(bad, today)
            self.assertIn('cutoff_date', raised.exception.errors)

    def test_opening_balance_rules(self):  # INV-03, AC-09
        self.assertEqual(validate_opening_balance('100'), Decimal('100.00'))
        self.assertEqual(Account.create('Caja', 'BOB', 'CASH').opening_balance, Decimal('0.00'))
        for bad in (-1, '1.234', 1.5, 'abc', Decimal('NaN'), 10 ** 10):
            with self.assertRaises(AccountValidationError) as raised:
                validate_opening_balance(bad)
            self.assertIn('opening_balance', raised.exception.errors)


class Base(APITestCase):
    def setUp(self):
        self.company = make_company('A')
        self.other = make_company('B')
        self.client_a = self.login(make_admin(self.company, 'ana'))
        self.client_b = self.login(make_admin(self.other, 'beto'))

    @staticmethod
    def login(user):
        client = APIClient()
        authenticate(client, user)
        return client

    def enable(self, client=None):
        response = (client or self.client_a).post(ENABLE)
        self.assertEqual(response.status_code, 200, response.content)

    def disable(self, client=None, expected=200):
        response = (client or self.client_a).post(DISABLE)
        self.assertEqual(response.status_code, expected, response.content)
        return response


class LifecycleTests(Base):
    def test_enabling_creates_cutoff_today_and_one_open_period(self):  # AC-06
        self.enable()
        body = self.client_a.get(SETTINGS).json()
        self.assertEqual((body['cutoff_date'], body['locked'], body['gaps']), (TODAY.isoformat(), False, []))
        self.assertEqual(SettingsModel.objects.filter(company_id=self.company.id).count(), 1)
        self.assertEqual(CoveragePeriodModel.objects.filter(company_id=self.company.id, ended_at=None).count(), 1)

    def test_repeating_enable_disable_enable_does_not_duplicate_or_move_anything(self):  # AC-03
        self.enable()
        cutoff = SettingsModel.objects.get(company_id=self.company.id).cutoff_date
        account = DjangoAccountRepository(self.company.id).save(Account.create('Banco', 'BOB', 'BANK', '250.00'))
        self.enable()
        self.disable()
        self.enable()
        self.enable()
        self.assertEqual(SettingsModel.objects.filter(company_id=self.company.id).count(), 1)
        self.assertEqual(SettingsModel.objects.get(company_id=self.company.id).cutoff_date, cutoff)
        self.assertEqual(CoveragePeriodModel.objects.filter(company_id=self.company.id).count(), 2)
        self.assertEqual(CoveragePeriodModel.objects.filter(company_id=self.company.id, ended_at=None).count(), 1)
        self.assertEqual(AccountModel.objects.get(pk=account.id).opening_balance, Decimal('250.00'))
        self.assertEqual(EntryModel.objects.count(), 0)

    def test_reactivation_leaves_a_gap_and_creates_no_movements(self):  # AC-07
        self.enable()
        SettingsModel.objects.filter(company_id=self.company.id).update(cutoff_date=TODAY - timedelta(days=60))
        past = timezone.now() - timedelta(days=10)
        CoveragePeriodModel.objects.filter(company_id=self.company.id).update(started_at=past - timedelta(days=20))
        self.disable()
        CoveragePeriodModel.objects.filter(company_id=self.company.id, ended_at__isnull=False).update(
            ended_at=past)
        self.enable()
        CoveragePeriodModel.objects.filter(company_id=self.company.id, ended_at=None).update(
            started_at=past + timedelta(days=4))
        gap = self.client_a.get(SETTINGS).json()['gaps']
        self.assertEqual(len(gap), 1)
        during = (past + timedelta(days=2)).astimezone().date()
        self.assertEqual(services.coverage_status(self.company.id, during).reason, 'in_gap')
        self.assertEqual(EntryModel.objects.count(), 0)

    def test_other_company_is_isolated(self):  # EDGE-04
        self.enable()
        self.assertIsNone(self.client_b.get(SETTINGS).json()['cutoff_date'])
        self.assertFalse(SettingsModel.objects.filter(company_id=self.other.id).exists())

    def test_disabled_company_reports_no_coverage(self):  # AC-07
        status = services.coverage_status(self.company.id, TODAY)
        self.assertEqual((status.enabled, status.covered, status.reason), (False, False, 'accounting_disabled'))
        self.enable()
        self.assertTrue(services.coverage_status(self.company.id, TODAY).covered)
        self.assertEqual(services.coverage_status(self.company.id, TODAY - timedelta(days=1)).reason, 'before_cutoff')


class CutoffTests(Base):
    def test_cutoff_changes_until_there_are_movements_then_locks(self):  # AC-06, INV-02
        self.enable()
        earlier = (TODAY - timedelta(days=30)).isoformat()
        self.assertEqual(self.client_a.patch(SETTINGS, {'cutoff_date': earlier}, format='json').json()['cutoff_date'],
                         earlier)
        account = DjangoAccountRepository(self.company.id).save(Account.create('Caja', 'BOB', 'CASH'))
        from modules.accounting.tests.test_entry_service import entry_input
        from django.db import transaction
        with transaction.atomic():
            services.record_entry(self.company.id, entry_input(account))
        locked = self.client_a.patch(SETTINGS, {'cutoff_date': TODAY.isoformat()}, format='json')
        self.assertEqual((locked.status_code, locked.json()['code']), (409, 'cutoff_locked'))
        self.assertTrue(self.client_a.get(SETTINGS).json()['locked'])

    def test_future_or_missing_cutoff_is_rejected(self):  # EDGE-01
        self.enable()
        future = (TODAY + timedelta(days=1)).isoformat()
        self.assertEqual(self.client_a.patch(SETTINGS, {'cutoff_date': future}, format='json').status_code, 400)
        self.assertEqual(self.client_a.patch(SETTINGS, {}, format='json').status_code, 400)

    def test_cannot_set_cutoff_before_ever_enabling(self):
        response = self.client_a.patch(SETTINGS, {'cutoff_date': TODAY.isoformat()}, format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'accounting_disabled'))

    def test_company_with_ledger_gets_its_cutoff_from_the_first_entry(self):  # AC-11
        account = DjangoAccountRepository(self.company.id).save(Account.create('Caja', 'BOB', 'CASH'))
        from modules.accounting.tests.test_entry_service import entry_input
        from django.db import transaction
        with transaction.atomic():
            services.record_entry(self.company.id, entry_input(account, payment_date=date(2026, 5, 3)))
        before = EntryModel.objects.count()
        from modules.modularity.infrastructure.django.models import CompanyModuleModel
        CompanyModuleModel.objects.create(company_id=self.company.id, module_key='accounting')
        body = self.client_a.get(SETTINGS).json()
        self.assertEqual((body['cutoff_date'], body['locked']), ('2026-05-03', True))
        self.assertEqual(EntryModel.objects.count(), before)
        self.assertEqual(self.client_a.get(SETTINGS).json()['cutoff_date'], '2026-05-03')


class DisableBlockersTests(Base):
    def test_disable_is_blocked_while_open_outflows_exist(self):  # AC-08, INV-05
        self.enable()
        with mock.patch('modules.accounting.infrastructure.lifecycle.DjangoOutflowLedger.open_count',
                        return_value=3):
            response = self.disable(expected=409)
        body = response.json()
        self.assertEqual(body['code'], 'disable_blocked')
        self.assertIn('3', body['blockers'][0])
        modules = {m['key']: m['enabled'] for m in self.client_a.get('/api/modules/').json()}
        self.assertTrue(modules['accounting'])
        self.assertEqual(CoveragePeriodModel.objects.filter(company_id=self.company.id, ended_at=None).count(), 1)

    def test_disable_is_allowed_without_outflows_even_with_income_entries(self):  # AC-08
        self.enable()
        self.disable()
        modules = {m['key']: m['enabled'] for m in self.client_a.get('/api/modules/').json()}
        self.assertFalse(modules['accounting'])


class OpeningBalanceApiTests(Base):
    def test_opening_balance_is_stored_validated_and_locked_by_movements(self):  # AC-09
        created = self.client_a.post(ACCOUNTS, {'name': 'Banco', 'currency': 'BOB', 'kind': 'BANK',
                                                'opening_balance': '1000.50'}, format='json')
        self.assertEqual((created.status_code, created.json()['opening_balance']), (201, '1000.50'))
        default = self.client_a.post(ACCOUNTS, {'name': 'Caja', 'currency': 'BOB', 'kind': 'CASH'}, format='json')
        self.assertEqual(default.json()['opening_balance'], '0.00')
        url = f'{ACCOUNTS}{created.json()["id"]}/'
        self.assertEqual(self.client_a.patch(url, {'opening_balance': '-5'}, format='json').status_code, 400)
        self.assertEqual(self.client_a.patch(url, {'opening_balance': '1.234'}, format='json').status_code, 400)
        changed = self.client_a.patch(url, {'opening_balance': '1500.00'}, format='json')
        self.assertEqual(changed.json()['opening_balance'], '1500.00')
        from modules.accounting.tests.test_entry_service import entry_input
        from django.db import transaction
        account = DjangoAccountRepository(self.company.id).get(created.json()['id'])
        with transaction.atomic():
            services.record_entry(self.company.id, entry_input(account))
        locked = self.client_a.patch(url, {'opening_balance': '2000.00'}, format='json')
        self.assertEqual((locked.status_code, locked.json()['code']), (409, 'account_has_entries'))
        same = self.client_a.patch(url, {'opening_balance': '1500.00'}, format='json')
        self.assertEqual(same.status_code, 200)


class EntriesCoverageTests(Base):
    def test_ledger_exposes_cutoff_and_gaps(self):  # AC-10
        self.enable()
        body = self.client_a.get('/api/accounting/entries/').json()
        self.assertEqual(body['coverage']['cutoff_date'], TODAY.isoformat())
        self.assertEqual(body['coverage']['gaps'], [])


class ExpenseIndependenceTests(ExpensesApiTestCase):
    def test_expense_without_accounting_creates_no_movement(self):  # AC-01
        before = EntryModel.objects.count()
        expense = self.expense()
        self.assertEqual(expense['status'], 'ACTIVE')
        self.assertEqual(EntryModel.objects.count(), before)

    def test_enabling_accounting_changes_nothing_historical(self):  # AC-02
        expense = self.expense()
        before = (ExpenseModel.objects.count(), EntryModel.objects.count(), AccountModel.objects.count())
        self.assertEqual(self.client.post(ENABLE).status_code, 200)
        self.assertEqual((ExpenseModel.objects.count(), EntryModel.objects.count(), AccountModel.objects.count()),
                         before)
        self.assertEqual(ExpenseModel.objects.get(pk=expense['id']).status, 'ACTIVE')

    def test_voiding_a_pre_cutoff_expense_without_movement_does_not_touch_accounts(self):  # AC-05
        old = self.expense(expense_date='2026-01-05')
        account = DjangoAccountRepository(self.company.id).save(Account.create('Banco', 'BOB', 'BANK', '300.00'))
        self.assertEqual(self.client.post(ENABLE).status_code, 200)
        entries = EntryModel.objects.count()
        self.void(old)
        self.assertEqual(EntryModel.objects.count(), entries)
        self.assertEqual(AccountModel.objects.get(pk=account.id).opening_balance, Decimal('300.00'))
        self.assertFalse(services.coverage_status(self.company.id, date(2026, 1, 5)).covered)


class PurchasePaymentIndependenceTests(PaymentApiTestCase):
    def test_paying_a_purchase_without_accounting_creates_no_movement(self):  # AC-01
        before = EntryModel.objects.count()
        purchase = self.confirmed_purchase()
        self.pay(purchase, '20.00')
        self.assertEqual(self.detail(purchase)['paid_total'], '20.00')
        self.assertEqual(EntryModel.objects.count(), before)

    def test_paying_after_enabling_accounting_still_works_and_adds_no_entry(self):  # AC-02
        purchase = self.confirmed_purchase()
        self.assertEqual(self.client.post(ENABLE).status_code, 200)
        self.pay(purchase, '20.00')
        self.assertEqual(EntryModel.objects.count(), 0)


class BoundaryTests(SimpleTestCase):
    def test_accounting_does_not_import_expenses_or_purchases(self):  # AC-12, INV-06
        root = Path(__file__).resolve().parents[1]
        offenders = []
        for path in root.rglob('*.py'):
            parts = path.relative_to(root).parts
            if 'tests' in parts or 'migrations' in parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
                offenders += [f'{path.name}: {n}' for n in names
                              if n.startswith(('modules.expenses', 'modules.purchases'))]
        self.assertEqual(offenders, [])

    def test_purchases_and_expenses_declare_no_dependency_on_each_other(self):  # AC-12
        from modules.sales.tests.test_boundaries import ALLOWED_DEPENDENCIES
        self.assertNotIn('expenses', ALLOWED_DEPENDENCIES['purchases'])
        self.assertNotIn('purchases', ALLOWED_DEPENDENCIES['expenses'])
        self.assertNotIn('expenses', ALLOWED_DEPENDENCIES['accounting'])
        self.assertNotIn('purchases', ALLOWED_DEPENDENCIES['accounting'])
