"""PB-ACC-002: reglas del agregado Entry (INV-01, INV-02, INV-05; AC-01)."""
from dataclasses import FrozenInstanceError
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.accounting.domain.entry import Entry, EntryValidationError


def make(**overrides):
    data = dict(account_id=uuid4(), currency='BOB', amount=Decimal('100.00'), payment_date=date(2026, 11, 1),
                method='CASH', origin_kind='PRODUCT', origin_id=uuid4())
    data.update(overrides)
    return Entry.record(**data)


class EntryTests(SimpleTestCase):
    def test_valid_entry_keeps_all_fields(self):
        entry = make(origin_document_ref='P-1', receipt_number='CB-000001', recorded_by=3, recorded_by_name='Ana')
        self.assertEqual((entry.amount, entry.currency, entry.method), (Decimal('100.00'), 'BOB', 'CASH'))
        self.assertEqual((entry.receipt_number, entry.recorded_by, entry.recorded_by_name), ('CB-000001', 3, 'Ana'))

    def test_amount_must_be_a_positive_decimal_with_two_places(self):  # INV-01
        for bad in (Decimal('0'), Decimal('-1'), Decimal('1.234'), 1.5, 'abc', None, Decimal('NaN'),
                    Decimal('10000000000.00')):
            with self.assertRaises(EntryValidationError, msg=repr(bad)) as ctx:
                make(amount=bad)
            self.assertIn('amount', ctx.exception.errors)
        self.assertEqual(make(amount='12.5').amount, Decimal('12.50'))

    def test_method_currency_and_origin_come_from_the_catalog(self):  # INV-02
        for field, value in (('method', 'CHEQUE'), ('currency', 'EUR'), ('origin_kind', 'ORDER')):
            with self.assertRaises(EntryValidationError) as ctx:
                make(**{field: value})
            self.assertIn(field, ctx.exception.errors)

    def test_payment_date_must_be_a_date(self):
        with self.assertRaises(EntryValidationError):
            make(payment_date=datetime(2026, 11, 1, 10, 0))
        with self.assertRaises(EntryValidationError):
            make(payment_date='2026-11-01')

    def test_entry_is_immutable(self):  # INV-05
        with self.assertRaises(FrozenInstanceError):
            make().amount = Decimal('1')

    def test_differences_lists_incompatible_fields(self):
        base = make()
        same_origin = Entry.record(account_id=base.account_id, currency='BOB', amount=Decimal('50'),
                                   payment_date=base.payment_date, method='QR', origin_kind='PRODUCT',
                                   origin_id=base.origin_id)
        self.assertEqual(sorted(base.differences(same_origin)), ['amount', 'method'])
