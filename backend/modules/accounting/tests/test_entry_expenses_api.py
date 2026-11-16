"""CONT-02: lectura de egresos y reversiones en la API del libro (AC-06, AC-07)."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import transaction

from modules.accounting import services
from modules.accounting.tests.test_entries_api import ENTRIES, EntriesApiBase, enable
from modules.accounting.tests.test_entry_expenses import classification, expense_input


class ExpenseEntriesApiTests(EntriesApiBase):
    def setUp(self):
        super().setUp()
        enable(self.company_a, 'expenses')
        self.alquiler = classification(self.company_a)

    def seed(self):
        self.record(self.company_a, self.caja, '250.00', date(2026, 11, 1))
        data = expense_input(self.banco, self.alquiler.id, amount=Decimal('100.00'))
        with transaction.atomic():
            services.record_entry(self.company_a.id, data)
        return data

    def test_expense_rows_expose_direction_classification_and_reversal_links(self):  # AC-07
        data = self.seed()
        with transaction.atomic():
            services.reverse_entry(self.company_a.id, 'EXPENSE', data.origin_id, date(2026, 11, 12))
        rows = self.client_a.get(ENTRIES, {'direction': 'EXPENSE'}).json()['results']
        self.assertEqual([(r['direction'], r['operation']) for r in rows], [('EXPENSE', 'RECORD')])
        everything = self.client_a.get(ENTRIES).json()['results']
        original = next(r for r in everything if r['operation'] == 'RECORD' and r['direction'] == 'EXPENSE')
        reversal = next(r for r in everything if r['operation'] == 'REVERSAL')
        self.assertEqual(original['classification'], {'id': str(self.alquiler.id), 'name': 'Alquiler'})
        self.assertEqual((original['origin']['kind'], original['source']['available']), ('EXPENSE', True))
        self.assertEqual((original['reversed_by'], original['reversal_of']), (reversal['id'], None))
        self.assertEqual((reversal['reversal_of'], reversal['reversed_by'], reversal['direction']),
                         (original['id'], None, 'INCOME'))
        detail = self.client_a.get(f"{ENTRIES}{reversal['id']}/").json()
        self.assertEqual(detail['reversal_of'], original['id'])

    def test_totals_keep_income_fields_and_add_the_direction_breakdown(self):  # AC-07
        data = self.seed()
        with transaction.atomic():
            services.reverse_entry(self.company_a.id, 'EXPENSE', data.origin_id, date(2026, 11, 12))
        totals = {t['currency']: t for t in self.client_a.get(ENTRIES).json()['totals']}['BOB']
        self.assertEqual((totals['amount'], totals['by_origin']), ('250.00', {'PRODUCT': '250.00', 'SERVICE': '0.00'}))
        self.assertEqual(totals['by_direction'], {'income': '250.00', 'expense': '100.00', 'reversed_income': '0.00',
                                                  'reversed_expense': '100.00', 'net': '250.00'})
        self.assertEqual(totals['count'], 3)

    def test_direction_and_new_origin_filters_and_unknown_values(self):  # AC-07
        self.seed()
        income = self.client_a.get(ENTRIES, {'direction': 'INCOME'}).json()
        expense = self.client_a.get(ENTRIES, {'direction': 'EXPENSE'}).json()
        self.assertEqual((income['count'], expense['count']), (1, 1))
        self.assertEqual(self.client_a.get(ENTRIES, {'origin': 'EXPENSE'}).json()['count'], 1)
        self.assertEqual(self.client_a.get(ENTRIES, {'origin': 'PURCHASE_PAYMENT'}).json()['count'], 0)
        self.assertEqual(self.client_a.get(ENTRIES, {'direction': 'X'}).status_code, 400)

    def test_other_company_does_not_see_expenses_and_the_ledger_has_no_write_routes(self):  # AC-05
        self.seed()
        self.assertEqual(self.client_b.get(ENTRIES).json()['count'], 0)
        self.assertEqual(self.client_a.post(ENTRIES, {}, format='json').status_code, 405)
        self.assertEqual(self.client_a.delete(f'{ENTRIES}{uuid4()}/').status_code, 405)
