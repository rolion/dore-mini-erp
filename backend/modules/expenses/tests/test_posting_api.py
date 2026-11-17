"""GAS-01: gastos contabilizados por partida doble con cuenta de gasto y de pago (BD real, Contabilidad real)."""
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from modules.accounting import services as accounting
from modules.accounting.application.use_cases import ConfigureMethod
from modules.accounting.infrastructure.django.models import AccountModel, FiscalPeriodModel, JournalEntryModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository, DjangoMethodMappingRepository
from modules.accounting.tests.journal_support import make_account, make_period, money_account
from modules.accounting.tests.test_entries_api import enable
from modules.accounts.testing import authenticate, make_admin, make_company
from modules.expenses.infrastructure.django.models import ExpenseModel

EXPENSES = '/api/expenses/'
CATEGORIES = '/api/expense-categories/'
OPTIONS = '/api/expenses/posting-options/'
TODAY = timezone.localdate()


class PostingApiBase(APITestCase):
    def setUp(self):
        self.company = make_company('A')
        self.other = make_company('B')
        enable(self.company, 'accounting', 'expenses')
        authenticate(self.client, make_admin(self.company, username='ana'))
        accounts = DjangoAccountRepository(self.company.id)
        self.caja = money_account(accounts, 'Caja', '110101', 'CASH')
        self.banco = money_account(accounts, 'Banco', '110102')
        self.alquiler = make_account(self.company.id, 'Alquiler', 'EXPENSE', '510001')
        self.luz = make_account(self.company.id, 'Luz', 'EXPENSE', '510002')
        self.cxc = make_account(self.company.id, 'Cuentas por cobrar', 'ASSET', '112001')
        self.period = make_period(self.company.id, 'Año', TODAY - timedelta(days=200), TODAY + timedelta(days=100))
        self.category = self.client.post(CATEGORIES, {'name': 'Alquiler'}, format='json').json()
        accounting.set_category_account(self.company.id, uuid4().__class__(self.category['id']), self.alquiler.id)
        self.map_method('BANK_TRANSFER', self.banco)
        self.map_method('CASH', self.caja)

    def map_method(self, code, account):
        ConfigureMethod(DjangoAccountRepository(self.company.id), DjangoMethodMappingRepository(self.company.id)
                        ).execute(code, account.id, True)

    def body(self, **extra):
        return {'description': 'Alquiler del local', 'amount': '500.00', 'category_id': self.category['id'],
                'expense_date': TODAY.isoformat(), 'payment_method': 'BANK_TRANSFER', **extra}

    def create(self, expected=201, **extra):
        response = self.client.post(EXPENSES, self.body(**extra), format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def lines(self, expense):
        entry = accounting.find_automatic_entry(self.company.id, 'EXPENSE_RECORD', expense['id'])
        return [(line.account_id, line.debit, line.credit) for line in entry.lines] if entry else None


class RegisterPostedExpenseTests(PostingApiBase):
    def test_rent_paid_from_the_bank_posts_debit_rent_credit_bank(self):  # AC-01
        created = self.create()
        self.assertTrue(created['posted'])
        self.assertEqual(created['expense_account']['id'], str(self.alquiler.id))
        self.assertEqual(created['payment_account']['id'], str(self.banco.id))
        self.assertEqual(self.lines(created), [(self.alquiler.id, Decimal('500.00'), 0),
                                               (self.banco.id, 0, Decimal('500.00'))])
        self.assertEqual(ExpenseModel.objects.count(), 1)
        detail = self.client.get(f'{EXPENSES}{created["id"]}/').json()
        self.assertEqual(detail['journal_entry_id'],
                         str(accounting.find_automatic_entry(self.company.id, 'EXPENSE_RECORD', created['id']).id))

    def test_chosen_accounts_replace_the_defaults(self):  # AC-01
        created = self.create(expense_account_id=str(self.luz.id), payment_account_id=str(self.caja.id))
        self.assertEqual(self.lines(created), [(self.luz.id, Decimal('500.00'), 0), (self.caja.id, 0, Decimal('500.00'))])

    def test_invalid_foreign_inactive_or_misclassified_accounts_are_rejected_and_nothing_is_saved(self):  # AC-02, AC-11
        foreign = make_account(self.other.id, 'Ajena', 'EXPENSE', '510009')
        AccountModel.objects.filter(pk=self.luz.id).update(is_active=False)
        for field, account in (('expense_account_id', foreign.id), ('expense_account_id', uuid4()),
                               ('expense_account_id', self.luz.id), ('expense_account_id', self.banco.id),
                               ('payment_account_id', self.alquiler.id), ('payment_account_id', self.cxc.id)):
            with self.subTest(field=field, account=account):
                body = self.create(expected=400, **{field: str(account)})
                self.assertIn(field, body)
        self.assertEqual(ExpenseModel.objects.count(), 0)
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 0)

    def test_a_closed_or_missing_period_fails_with_409_and_no_expense(self):  # AC-03
        body = self.create(expected=409, expense_date=(TODAY + timedelta(days=300)).isoformat())
        self.assertEqual(body['code'], 'date_outside_fiscal_period')
        FiscalPeriodModel.objects.filter(pk=self.period.id).update(status='CLOSED')
        self.assertEqual(self.create(expected=409)['code'], 'fiscal_period_closed')
        self.assertEqual(ExpenseModel.objects.count(), 0)

    def test_missing_configuration_is_reported_and_nothing_is_saved(self):  # AC-07
        other_category = self.client.post(CATEGORIES, {'name': 'Otros'}, format='json').json()
        body = self.create(expected=400, category_id=other_category['id'], payment_method='QR')
        self.assertEqual(body['code'], 'posting_configuration_missing')
        self.assertEqual({i['code'] for i in body['issues']}, {'category_unconfigured', 'method_unconfigured'})
        self.assertEqual(ExpenseModel.objects.count(), 0)

    def test_without_accounting_it_saves_without_accounts_and_ignores_chosen_ones(self):  # AC-06
        enable(self.other, 'expenses')
        client = APIClient()
        authenticate(client, make_admin(self.other, username='beto'))
        category = client.post(CATEGORIES, {'name': 'X'}, format='json').json()
        response = client.post(EXPENSES, {'description': 'x', 'amount': '5', 'category_id': category['id'],
                                          'expense_date': TODAY.isoformat(),
                                          'expense_account_id': str(self.luz.id)}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual((response.json()['posted'], response.json()['expense_account']), (False, None))
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.other.id).count(), 0)

    def test_changing_the_configuration_later_does_not_change_the_expense(self):  # AC-05
        created = self.create()
        accounting.set_category_account(self.company.id, uuid4().__class__(self.category['id']), self.luz.id)
        self.map_method('BANK_TRANSFER', self.caja)
        detail = self.client.get(f'{EXPENSES}{created["id"]}/').json()
        self.assertEqual((detail['expense_account']['id'], detail['payment_account']['id']),
                         (str(self.alquiler.id), str(self.banco.id)))
        self.assertEqual(self.lines(created)[0][0], self.alquiler.id)


class IdempotencyTests(PostingApiBase):
    def test_retrying_with_the_same_key_does_not_duplicate_the_expense_or_the_entry(self):  # AC-04
        key = str(uuid4())
        first = self.create(idempotency_key=key)
        response = self.client.post(EXPENSES, self.body(idempotency_key=key), format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()['id'], response.json()['replayed']), (first['id'], True))
        self.assertFalse(first['replayed'])
        self.assertEqual(ExpenseModel.objects.count(), 1)
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 1)

    def test_the_same_key_with_other_data_is_a_conflict(self):  # AC-04
        key = str(uuid4())
        self.create(idempotency_key=key)
        body = self.create(expected=409, idempotency_key=key, amount='600.00')
        self.assertEqual(body['code'], 'idempotency_key_reused')
        self.assertEqual(ExpenseModel.objects.count(), 1)

    def test_a_retry_after_the_configuration_changed_returns_the_existing_expense(self):  # AC-04, AC-05
        key = str(uuid4())
        first = self.create(idempotency_key=key)
        accounting.set_category_account(self.company.id, uuid4().__class__(self.category['id']), None)
        self.assertEqual(self.create(expected=200, idempotency_key=key)['id'], first['id'])

    def test_keys_are_scoped_by_company(self):  # AC-11
        key = str(uuid4())
        self.create(idempotency_key=key)
        enable(self.other, 'expenses')
        client = APIClient()
        authenticate(client, make_admin(self.other, username='beto'))
        category = client.post(CATEGORIES, {'name': 'X'}, format='json').json()
        response = client.post(EXPENSES, {'description': 'x', 'amount': '5', 'category_id': category['id'],
                                          'expense_date': TODAY.isoformat(), 'idempotency_key': key}, format='json')
        self.assertEqual(response.status_code, 201, response.content)


class LockAndVoidTests(PostingApiBase):
    def test_a_posted_expense_locks_its_financial_fields_but_not_the_descriptive_ones(self):  # AC-08
        created = self.create()
        url = f'{EXPENSES}{created["id"]}/'
        for change in ({'amount': '600.00'}, {'expense_date': (TODAY - timedelta(days=1)).isoformat()},
                       {'payment_method': 'CASH'}):
            with self.subTest(change=change):
                response = self.client.patch(url, change, format='json')
                self.assertEqual((response.status_code, response.json()['code']), (409, 'expense_posted_locked'))
        ok = self.client.patch(url, {'description': 'Nuevo', 'supplier_name': 'Dueño', 'notes': 'n',
                                     'amount': '500.00'}, format='json')
        self.assertEqual((ok.status_code, ok.json()['description']), (200, 'Nuevo'))
        self.assertEqual(self.lines(created)[0][1], Decimal('500.00'))

    def test_voiding_a_posted_expense_reverses_the_entry(self):  # AC-09
        created = self.create()
        response = self.client.post(f'{EXPENSES}{created["id"]}/void/')
        self.assertEqual((response.status_code, response.json()['status']), (200, 'VOIDED'))
        entry = accounting.find_automatic_entry(self.company.id, 'EXPENSE_RECORD', created['id'])
        reversal = JournalEntryModel.objects.get(reverses_id=entry.id)
        self.assertEqual(reversal.company_id, self.company.id)
        self.assertEqual(self.client.post(f'{EXPENSES}{created["id"]}/void/').status_code, 409)
        self.assertEqual(JournalEntryModel.objects.filter(reverses_id=entry.id).count(), 1)

    def test_voiding_in_a_closed_period_fails_and_keeps_the_expense_active(self):  # AC-09
        created = self.create()
        FiscalPeriodModel.objects.filter(pk=self.period.id).update(status='CLOSED')
        response = self.client.post(f'{EXPENSES}{created["id"]}/void/')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'fiscal_period_closed'))
        self.assertEqual(ExpenseModel.objects.get(pk=created['id']).status, 'ACTIVE')

    def test_voiding_an_expense_without_entry_needs_no_reversal(self):  # AC-10
        enable(self.other, 'expenses')
        client = APIClient()
        authenticate(client, make_admin(self.other, username='beto'))
        category = client.post(CATEGORIES, {'name': 'X'}, format='json').json()
        created = client.post(EXPENSES, {'description': 'x', 'amount': '5', 'category_id': category['id'],
                                         'expense_date': TODAY.isoformat()}, format='json').json()
        self.assertFalse(created['posted'])
        self.assertEqual(client.post(f'{EXPENSES}{created["id"]}/void/').status_code, 200)
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.other.id).count(), 0)


class PostingOptionsTests(PostingApiBase):
    def test_returns_defaults_and_eligible_accounts(self):
        body = self.client.get(OPTIONS, {'expense_date': TODAY.isoformat(), 'category_id': self.category['id'],
                                         'payment_method': 'bank_transfer'}).json()
        self.assertTrue(body['covered'])
        self.assertEqual((body['expense_account']['id'], body['payment_account']['id']),
                         (str(self.alquiler.id), str(self.banco.id)))
        self.assertEqual(body['issues'], [])
        self.assertEqual({a['id'] for a in body['payment_accounts']}, {str(self.caja.id), str(self.banco.id)})
        self.assertEqual({a['id'] for a in body['expense_accounts']}, {str(self.alquiler.id), str(self.luz.id)})

    def test_reports_what_is_missing_and_nothing_without_coverage(self):
        body = self.client.get(OPTIONS, {'expense_date': TODAY.isoformat(), 'payment_method': 'QR'}).json()
        self.assertEqual({i['code'] for i in body['issues']}, {'category_required', 'method_unconfigured'})
        enable(self.other, 'expenses')
        client = APIClient()
        authenticate(client, make_admin(self.other, username='beto'))
        none = client.get(OPTIONS, {'expense_date': TODAY.isoformat()}).json()
        self.assertEqual((none['covered'], none['issues'], none['expense_accounts']), (False, [], []))

    def test_requires_a_date(self):
        self.assertEqual(self.client.get(OPTIONS).status_code, 400)
