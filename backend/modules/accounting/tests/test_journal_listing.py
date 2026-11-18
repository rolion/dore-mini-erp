"""CONT-11: lectura del libro de asientos: orden total, filtros, aislamiento por empresa y número de consultas."""
from datetime import date

from django.db import connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from modules.accounting import services
from modules.accounting.application.journal_queries import (
    GetJournalEntry,
    JournalFilters,
    ListJournalEntries,
)
from modules.accounting.domain.journal import JournalEntryNotFound
from modules.accounting.infrastructure.django.models import JournalEntryModel
from modules.accounting.infrastructure.django.repositories import DjangoJournalRepository
from modules.accounting.tests.journal_support import DAY, automatic, entry_input, make_account, make_period
from modules.accounts.testing import make_company


class JournalListingTests(TestCase):
    def setUp(self):
        self.company = make_company('A')
        self.other = make_company('B')
        self.cash = make_account(self.company.id, 'Caja', code='111001')
        self.bank = make_account(self.company.id, 'Banco', code='111002')
        self.income = make_account(self.company.id, 'Ingresos', 'INCOME', code='411001')
        make_period(self.company.id)
        make_period(self.other.id)
        self.repo = DjangoJournalRepository(self.company.id)

    def post(self, **overrides):
        with transaction.atomic():
            return services.post_journal_entry(
                self.company.id, entry_input(self.cash, self.bank, self.income, **overrides)).entry.id

    def ids(self, **filters):
        return [row.id for row in ListJournalEntries(self.repo).execute(JournalFilters(**filters))]

    def test_orders_by_date_then_creation_then_id_descending(self):  # INV-04
        for day in (12, 10, 11, 12):
            self.post(accounting_date=DAY.replace(day=day))
        JournalEntryModel.objects.update(created_at=JournalEntryModel.objects.first().created_at)
        expected = list(JournalEntryModel.objects.order_by('-accounting_date', '-created_at', '-id')
                        .values_list('id', flat=True))
        self.assertEqual(self.ids(), expected)
        dates = [row.accounting_date for row in ListJournalEntries(self.repo).execute(JournalFilters())]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_filters_combine(self):
        self.post(accounting_date=date(2026, 5, 1))
        manual = self.post(accounting_date=date(2026, 5, 20))
        auto = self.post(accounting_date=date(2026, 6, 1), **automatic())
        self.assertEqual(set(self.ids(source='MANUAL')), {manual, self.ids(date_to=date(2026, 5, 1))[0]})
        self.assertEqual(self.ids(source='AUTOMATIC'), [auto])
        self.assertEqual(self.ids(date_from=date(2026, 5, 15), source='MANUAL'), [manual])
        self.assertEqual(self.ids(origin_kind='SERVICE_PAYMENT'), [auto])
        self.assertEqual(len(self.ids(account_id=self.cash.id)), 3)
        self.assertEqual(self.ids(account_id=make_account(self.company.id, 'Otra', code='111003').id), [])

    def test_does_not_return_other_companies_entries(self):  # INV-05
        entry_id = self.post()
        other_repo = DjangoJournalRepository(self.other.id)
        self.assertEqual(list(ListJournalEntries(other_repo).execute(JournalFilters())), [])
        with self.assertRaises(JournalEntryNotFound):
            GetJournalEntry(other_repo).execute(entry_id)
        self.assertEqual(GetJournalEntry(self.repo).execute(entry_id).id, entry_id)

    def test_filtering_by_an_account_of_another_company_finds_nothing(self):  # INV-05
        self.post()
        foreign = make_account(self.other.id, 'Ajena', code='111009')
        self.assertEqual(self.ids(account_id=foreign.id), [])

    def test_listing_a_page_uses_a_constant_number_of_queries(self):  # sin N+1
        self.post()

        def queries_for_page():
            with CaptureQueriesContext(connection) as captured:
                rows = list(ListJournalEntries(self.repo).execute(JournalFilters()))
                [(row.reversed_by_entry if hasattr(row, 'reversed_by_entry') else None, row.total) for row in rows]
            return len(captured)

        baseline = queries_for_page()
        for _ in range(5):
            self.post()
        self.assertEqual(queries_for_page(), baseline)
        self.assertLessEqual(baseline, 1)
