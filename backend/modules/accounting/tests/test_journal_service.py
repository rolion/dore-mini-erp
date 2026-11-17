"""CONT-02: contrato `post_journal_entry` / `reverse_journal_entry` (AC-01..AC-12; INV-01..11)."""
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.db import IntegrityError, connection
from django.test import TestCase

from modules.accounting import services
from modules.accounting.application.fiscal_periods import CloseFiscalPeriod
from modules.accounting.domain.account import Account
from modules.accounting.infrastructure.django.models import (
    EntryModel,
    JournalEntryModel,
    JournalLineModel,
)
from modules.accounting.infrastructure.django.repositories import DjangoAccountClassRepository, DjangoAccountRepository
from modules.accounting.infrastructure.django.repositories import DjangoFiscalPeriodRepository
from modules.accounting.tests.journal_support import DAY, automatic, entry_input, make_account, make_period, sale_lines
from modules.accounts.testing import make_company


class JournalBase(TestCase):
    def setUp(self):
        self.company = make_company('A')
        self.other = make_company('B')
        self.cash = make_account(self.company.id, 'Caja')
        self.bank = make_account(self.company.id, 'Banco')
        self.income = make_account(self.company.id, 'Ingresos servicios', 'INCOME')
        self.period = make_period(self.company.id)

    def post(self, **overrides):
        return services.post_journal_entry(self.company.id, entry_input(self.cash, self.bank, self.income, **overrides))


class PostTests(JournalBase):
    def test_a_balanced_entry_is_confirmed_with_header_lines_and_period(self):  # AC-01
        result = self.post()
        self.assertTrue(result.created)
        entry = result.entry
        self.assertEqual((entry.total, entry.currency, entry.source, entry.period_id),
                         (Decimal('500.00'), 'BOB', 'MANUAL', self.period.id))
        self.assertEqual([(x.debit, x.credit) for x in entry.lines],
                         [(Decimal('200.00'), 0), (Decimal('300.00'), 0), (0, Decimal('500.00'))])
        row = JournalEntryModel.objects.get(pk=entry.id)
        self.assertEqual((row.company_id, row.created_by, row.created_by_name), (self.company.id, 7, 'Ana'))
        self.assertEqual(JournalLineModel.objects.filter(entry_id=entry.id).count(), 3)

    def test_an_unbalanced_entry_persists_nothing(self):  # AC-01
        lines = sale_lines(self.cash, self.bank, self.income, income_amount='499.00')
        with self.assertRaises(services.JournalValidationError):
            self.post(lines=lines)
        self.assertEqual((JournalEntryModel.objects.count(), JournalLineModel.objects.count()), (0, 0))

    def test_invalid_shapes_are_rejected_without_persisting(self):  # AC-02
        one = [services.JournalLineInput(self.cash.id, debit=Decimal('5')),
               services.JournalLineInput(self.cash.id, credit=Decimal('5'))]
        negative = [services.JournalLineInput(self.cash.id, debit=Decimal('-5')),
                    services.JournalLineInput(self.bank.id, credit=Decimal('-5'))]
        both = [services.JournalLineInput(self.cash.id, debit=Decimal('5'), credit=Decimal('5')),
                services.JournalLineInput(self.bank.id, credit=Decimal('5'))]
        for lines in (one, negative, both):
            with self.subTest(lines=lines), self.assertRaises(services.JournalValidationError):
                self.post(lines=lines)
        self.assertEqual(JournalEntryModel.objects.count(), 0)

    def test_accounts_must_be_usable_in_the_company(self):  # AC-02, INV-04
        foreign = make_account(self.other.id, 'Caja ajena')
        inactive = make_account(self.company.id, 'Vieja', active=False)
        unclassified = DjangoAccountRepository(self.company.id).save(Account.create('Sin clase', 'BOB'))
        usd = make_account(self.company.id, 'Caja USD', currency='USD')
        for account in (foreign, inactive, unclassified, usd):
            lines = [services.JournalLineInput(account.id, debit=Decimal('5')),
                     services.JournalLineInput(self.income.id, credit=Decimal('5'))]
            with self.subTest(account=account.name), self.assertRaises(services.JournalValidationError):
                self.post(lines=lines)
        self.assertEqual(JournalEntryModel.objects.count(), 0)

    def test_a_disabled_class_rejects_new_entries(self):  # INV-04
        DjangoAccountClassRepository(self.company.id).set_enabled('INCOME', False)
        with self.assertRaises(services.JournalValidationError):
            self.post()

    def test_the_date_must_be_in_an_open_period(self):  # AC-02, INV-05
        with self.assertRaises(services.DateOutsideFiscalPeriod):
            self.post(accounting_date=date(2026, 7, 1))
        CloseFiscalPeriod(DjangoFiscalPeriodRepository(self.company.id)).execute(
            self.period.id, 'Ana', datetime(2026, 7, 2, tzinfo=timezone.utc))
        with self.assertRaises(services.FiscalPeriodClosed):
            self.post()
        self.assertEqual(JournalEntryModel.objects.count(), 0)

    def test_a_failing_line_rolls_back_header_and_origin(self):  # AC-04, INV-06
        with mock.patch('modules.accounting.infrastructure.django.repositories.JournalLineModel.objects.bulk_create',
                        side_effect=IntegrityError('boom')):
            with self.assertRaises(IntegrityError):
                self.post(**automatic())
        self.assertEqual(JournalEntryModel.objects.count(), 0)
        self.assertTrue(connection.in_atomic_block)  # la transacción del llamante sigue utilizable
        self.assertTrue(self.post(**automatic()).created)

    def test_an_automatic_entry_is_idempotent_by_origin(self):  # AC-03, INV-07
        origin = automatic()
        first, second = self.post(**origin), self.post(**origin)
        self.assertEqual((first.created, second.created, first.entry.id), (True, False, second.entry.id))
        self.assertEqual((first.entry.source, first.entry.origin_kind), ('AUTOMATIC', 'SERVICE_PAYMENT'))
        self.assertEqual(JournalEntryModel.objects.count(), 1)

    def test_a_retry_with_other_data_is_a_conflict(self):  # AC-03
        origin = automatic()
        self.post(**origin)
        with self.assertRaises(services.JournalConflict) as ctx:
            self.post(description='Otro', accounting_date=date(2026, 5, 11), **origin)
        self.assertEqual(sorted(ctx.exception.fields), ['accounting_date', 'description'])

    def test_a_retry_is_not_revalidated_after_the_account_was_deactivated(self):  # AC-03
        origin = automatic()
        first = self.post(**origin)
        account = DjangoAccountRepository(self.company.id).get(self.cash.id)
        account.deactivate()
        DjangoAccountRepository(self.company.id).save(account)
        self.assertEqual(self.post(**origin).entry.id, first.entry.id)

    def test_equal_operations_with_different_events_coexist(self):  # AC-03
        a, b = self.post(**automatic()), self.post(**automatic())
        self.assertNotEqual(a.entry.id, b.entry.id)
        self.assertEqual(JournalEntryModel.objects.count(), 2)

    def test_manual_entries_never_collide(self):  # INV-07
        self.assertNotEqual(self.post().entry.id, self.post().entry.id)

    def test_the_same_origin_in_two_companies_is_independent(self):  # INV-11
        origin = automatic()
        self.post(**origin)
        other_cash, other_bank = make_account(self.other.id, 'Caja'), make_account(self.other.id, 'Banco')
        other_income = make_account(self.other.id, 'Ingresos', 'INCOME')
        make_period(self.other.id)
        result = services.post_journal_entry(self.other.id, entry_input(other_cash, other_bank, other_income, **origin))
        self.assertTrue(result.created)

    def test_an_origin_in_the_legacy_ledger_is_rejected(self):  # AC-09, INV-10
        legacy = EntryModel.objects.create(
            company_id=self.company.id, account_id=self.cash.id, currency='BOB', amount=Decimal('10.00'),
            payment_date=DAY, payment_method='CASH', origin_kind='SERVICE_PAYMENT', origin_id=uuid4())
        with self.assertRaises(services.JournalConflict) as ctx:
            self.post(origin_kind=legacy.origin_kind, origin_id=legacy.origin_id)
        self.assertEqual(ctx.exception.code, 'origin_in_legacy_ledger')
        self.assertEqual(JournalEntryModel.objects.count(), 0)
        self.assertEqual(EntryModel.objects.count(), 1)  # el motor no escribe en el libro anterior


class ReverseTests(JournalBase):
    def test_reversal_neutralizes_every_line_and_links_the_original(self):  # AC-05
        original = self.post(**automatic()).entry
        result = services.reverse_journal_entry(self.company.id, original.id, date(2026, 5, 20), 'Cobro anulado', 9, 'Luis')
        reversal = result.entry
        self.assertTrue(result.created)
        self.assertEqual((reversal.reverses_id, reversal.reversal_reason, reversal.accounting_date),
                         (original.id, 'Cobro anulado', date(2026, 5, 20)))
        self.assertEqual((reversal.origin_id, reversal.origin_kind), (None, None))
        balances = services.journal_balances(self.company.id)
        for account in (self.cash, self.bank, self.income):
            self.assertEqual(balances[account.id].debit, balances[account.id].credit)
        self.assertEqual(services.get_journal_entry(self.company.id, original.id).reversed_by_id, reversal.id)
        self.assertEqual(services.get_journal_entry(self.company.id, original.id).lines, original.lines)  # no cambia

    def test_a_second_reversal_returns_the_same_one(self):  # AC-06
        original = self.post().entry
        first = services.reverse_journal_entry(self.company.id, original.id, DAY, 'Error')
        second = services.reverse_journal_entry(self.company.id, original.id, DAY, 'Error')
        self.assertEqual((first.created, second.created, first.entry.id), (True, False, second.entry.id))
        self.assertEqual(JournalEntryModel.objects.count(), 2)

    def test_a_reversal_cannot_be_reversed_and_needs_a_reason(self):  # AC-06
        original = self.post().entry
        with self.assertRaises(services.JournalValidationError):
            services.reverse_journal_entry(self.company.id, original.id, DAY, ' ')
        reversal = services.reverse_journal_entry(self.company.id, original.id, DAY, 'Error').entry
        with self.assertRaises(services.JournalValidationError):
            services.reverse_journal_entry(self.company.id, reversal.id, DAY, 'Otra')

    def test_reversal_uses_original_accounts_even_if_disabled(self):  # AC-07
        original = self.post().entry
        DjangoAccountClassRepository(self.company.id).set_enabled('INCOME', False)
        account = DjangoAccountRepository(self.company.id).get(self.cash.id)
        account.deactivate()
        DjangoAccountRepository(self.company.id).save(account)
        with self.assertRaises(services.JournalValidationError):
            self.post()
        self.assertTrue(services.reverse_journal_entry(self.company.id, original.id, DAY, 'Error').created)

    def test_with_a_closed_original_period_the_reversal_goes_to_an_open_one(self):  # AC-07
        original = self.post().entry
        july = make_period(self.company.id, 'Q3', date(2026, 7, 1), date(2026, 9, 30))
        CloseFiscalPeriod(DjangoFiscalPeriodRepository(self.company.id)).execute(
            self.period.id, 'Ana', datetime(2026, 7, 2, tzinfo=timezone.utc))
        with self.assertRaises(services.FiscalPeriodClosed):
            services.reverse_journal_entry(self.company.id, original.id, DAY, 'Error')
        reversal = services.reverse_journal_entry(self.company.id, original.id, date(2026, 7, 15), 'Error').entry
        self.assertEqual(reversal.period_id, july.id)
        self.assertEqual(services.get_journal_entry(self.company.id, original.id).period_id, self.period.id)

    def test_other_companies_cannot_read_or_reverse_an_entry(self):  # AC-10, INV-11
        original = self.post().entry
        with self.assertRaises(services.JournalEntryNotFound):
            services.get_journal_entry(self.other.id, original.id)
        with self.assertRaises(services.JournalEntryNotFound):
            services.reverse_journal_entry(self.other.id, original.id, DAY, 'x')


class ReconciliationTests(JournalBase):
    def test_every_entry_balances_in_sql_and_balances_match_lines(self):  # AC-11
        for _ in range(3):
            self.post()
        first = self.post(**automatic()).entry
        services.reverse_journal_entry(self.company.id, first.id, DAY, 'Error')
        with connection.cursor() as cursor:
            cursor.execute('SELECT entry_id FROM accounting_journal_line GROUP BY entry_id '
                           'HAVING SUM(debit) <> SUM(credit)')
            self.assertEqual(cursor.fetchall(), [])
        balances = services.journal_balances(self.company.id, [self.cash.id])
        self.assertEqual(list(balances), [self.cash.id])
        self.assertEqual(balances[self.cash.id].debit, Decimal('800.00'))
        self.assertEqual(balances[self.cash.id].credit, Decimal('200.00'))
        self.assertEqual(services.journal_balances(self.other.id), {})

    def test_database_rejects_a_line_with_both_sides(self):
        entry = self.post().entry
        with self.assertRaises(IntegrityError):
            JournalLineModel.objects.create(entry_id=entry.id, company_id=self.company.id, position=9,
                                            account_id=self.cash.id, debit=1, credit=1)


class ContractTests(TestCase):
    def test_functions_require_a_transaction(self):  # AC-12
        # TestCase envuelve en una transacción: se simula su ausencia como en las pruebas de `record_entry`.
        company = make_company('A')
        with mock.patch.object(services.connection, 'in_atomic_block', False):
            with self.assertRaises(services.EntryContractError):
                services.post_journal_entry(company.id, services.JournalEntryInput(DAY, 'x', []))
            with self.assertRaises(services.EntryContractError):
                services.reverse_journal_entry(company.id, uuid4(), DAY, 'x')
