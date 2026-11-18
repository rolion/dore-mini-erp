"""CONT-02: invariantes del asiento de partida doble, sin base de datos (INV-01..03, INV-09; AC-01, AC-02, AC-05, AC-06)."""
from datetime import date, datetime
from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from modules.accounting.domain.journal import (
    AUTOMATIC,
    MANUAL,
    JournalEntry,
    JournalLineInput,
    JournalValidationError,
)

CASH, BANK, INCOME = uuid4(), uuid4(), uuid4()
DAY = date(2026, 5, 10)


def post(lines, **kwargs):
    data = {'accounting_date': DAY, 'description': 'Servicio', 'currency': 'BOB', 'lines': lines}
    data.update(kwargs)
    return JournalEntry.post(**data)


def balanced():
    return [JournalLineInput(CASH, debit=Decimal('200.00')), JournalLineInput(BANK, debit=Decimal('300.00')),
            JournalLineInput(INCOME, credit=Decimal('500.00'))]


class PostTests(TestCase):
    def test_a_balanced_entry_with_three_accounts_is_confirmed(self):  # AC-01
        entry = post(balanced())
        self.assertEqual((entry.total_debit, entry.total_credit), (Decimal('500.00'), Decimal('500.00')))
        self.assertEqual(entry.source, MANUAL)
        self.assertEqual([line.position for line in entry.lines], [0, 1, 2])

    def test_an_unbalanced_entry_is_rejected(self):  # AC-01
        lines = balanced()
        lines[2] = JournalLineInput(INCOME, credit=Decimal('499.00'))
        with self.assertRaises(JournalValidationError) as ctx:
            post(lines)
        self.assertIn('lines', ctx.exception.errors)

    def test_a_single_account_is_rejected_even_with_two_lines(self):  # AC-02, INV-01
        with self.assertRaises(JournalValidationError):
            post([JournalLineInput(CASH, debit=Decimal('10')), JournalLineInput(CASH, credit=Decimal('10'))])

    def test_fewer_than_two_lines_is_rejected(self):  # AC-02
        with self.assertRaises(JournalValidationError):
            post([JournalLineInput(CASH, debit=Decimal('10'))])
        with self.assertRaises(JournalValidationError):
            post([])

    def test_negative_zero_both_sides_and_neither_side_are_rejected(self):  # AC-02, INV-02
        bad = [JournalLineInput(CASH, debit=Decimal('-5')), JournalLineInput(CASH, debit=Decimal('5'), credit=Decimal('5')),
               JournalLineInput(CASH), JournalLineInput(CASH, debit=Decimal('0.00'))]
        for line in bad:
            with self.subTest(line=line), self.assertRaises(JournalValidationError):
                post([line, JournalLineInput(INCOME, credit=Decimal('5'))])

    def test_floats_and_extra_decimals_are_rejected_and_exponents_accepted(self):  # AC-02, INV-02
        for amount in (10.5, True, Decimal('1.001'), Decimal('NaN'), Decimal('10') ** 10, 'x'):
            with self.subTest(amount=amount), self.assertRaises(JournalValidationError):
                post([JournalLineInput(CASH, debit=amount), JournalLineInput(INCOME, credit=Decimal('1'))])
        entry = post([JournalLineInput(CASH, debit=Decimal('1E+2')), JournalLineInput(INCOME, credit='100.00')])
        self.assertEqual(entry.total_debit, Decimal('100.00'))

    def test_sums_are_exact_decimals(self):  # AC-01
        lines = [JournalLineInput(CASH, debit=Decimal('0.10')), JournalLineInput(BANK, debit=Decimal('0.20')),
                 JournalLineInput(INCOME, credit=Decimal('0.30'))]
        self.assertEqual(post(lines).total_debit, Decimal('0.30'))

    def test_description_date_and_currency_are_validated(self):  # AC-02
        for kwargs in ({'description': '  '}, {'description': 'x' * 201}, {'accounting_date': datetime(2026, 5, 10)},
                       {'accounting_date': '2026-05-10'}, {'currency': 'EUR'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(JournalValidationError):
                post(balanced(), **kwargs)

    def test_automatic_entries_need_a_complete_origin(self):  # INV-07
        entry = post(balanced(), origin_kind='SALE_PAYMENT', origin_id=uuid4())
        self.assertEqual(entry.source, AUTOMATIC)
        for kwargs in ({'origin_kind': 'SALE_PAYMENT'}, {'origin_id': uuid4()},
                       {'origin_kind': 'SALE_PAYMENT', 'origin_id': 'abc'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(JournalValidationError):
                post(balanced(), **kwargs)


class ReverseTests(TestCase):
    def test_reversal_inverts_every_line_and_links_the_original(self):  # AC-05, INV-09
        original = post(balanced())
        reversal = original.reverse(date(2026, 6, 1), 'Error de captura', 7, 'Ana')
        self.assertEqual(reversal.reverses_id, original.id)
        self.assertEqual([(x.account_id, x.debit, x.credit) for x in reversal.lines],
                         [(x.account_id, x.credit, x.debit) for x in original.lines])
        self.assertEqual((reversal.total_debit, reversal.total_credit), (Decimal('500.00'), Decimal('500.00')))
        self.assertEqual((reversal.origin_id, reversal.origin_kind), (None, None))
        self.assertEqual(reversal.reversal_reason, 'Error de captura')

    def test_a_reversal_requires_reason_and_date_and_cannot_be_reversed(self):  # AC-06
        original = post(balanced())
        with self.assertRaises(JournalValidationError):
            original.reverse(date(2026, 6, 1), '  ')
        with self.assertRaises(JournalValidationError):
            original.reverse(datetime(2026, 6, 1), 'x')
        with self.assertRaises(JournalValidationError):
            original.reverse(date(2026, 6, 1), 'x' * 201)
        with self.assertRaises(JournalValidationError):
            original.reverse(date(2026, 6, 1), 'x').reverse(date(2026, 6, 2), 'y')


class DifferencesTests(TestCase):
    def test_same_business_data_has_no_differences_regardless_of_line_order(self):
        a = post(balanced())
        b = post(list(reversed(balanced())))
        self.assertEqual(a.differences(b), [])

    def test_reports_the_fields_that_differ(self):
        a = post(balanced())
        b = post(balanced(), description='Otro', accounting_date=date(2026, 5, 11))
        self.assertEqual(sorted(a.differences(b)), ['accounting_date', 'description'])
        c = post([JournalLineInput(CASH, debit=Decimal('500')), JournalLineInput(INCOME, credit=Decimal('500'))])
        self.assertEqual(a.differences(c), ['lines'])
