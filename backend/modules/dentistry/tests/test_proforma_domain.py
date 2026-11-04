from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.dentistry.domain.proforma import (
    DRAFT, PRESENTED, SUPERSEDED, DentalProforma, DentalProformaLine, DentalProformaStateError,
    DentalProformaValidationError, clean_piece,
)


def line(quantity='1', price='100', piece=''):
    return DentalProformaLine(uuid4(), uuid4(), 'Limpieza', Decimal(quantity), Decimal(price), piece)


def draft(lines=()):
    return DentalProforma.create(number='ODO-000001', customer_id=uuid4(), patient_name='Ana',
                                 date=date(2026, 11, 4), lines=lines)


class DentalProformaDomainTests(SimpleTestCase):
    def test_total_of_two_services(self):  # AC-01 / INV-01
        self.assertEqual(draft([line(price='100'), line(price='150')]).total, Decimal('250.00'))

    def test_subtotal_rounds_half_up(self):  # INV-01
        self.assertEqual(line(quantity='1.50', price='0.15').subtotal, Decimal('0.23'))

    def test_invalid_quantity_and_price_report_errors_per_line(self):  # AC-03
        for quantity, price in (('0', '1'), ('-1', '1'), ('1', '-0.01'), ('1.001', '1'), ('10000', '1')):
            with self.assertRaises(DentalProformaValidationError) as ctx:
                draft([line(), line(quantity, price)])
            errors = ctx.exception.errors['lines']
            self.assertEqual(errors[0], {})
            self.assertTrue(errors[1])

    def test_piece_is_optional_text_trimmed_up_to_20_characters(self):  # AC-02 / INV-04
        self.assertEqual(clean_piece(None), '')
        self.assertEqual(clean_piece('  18 '), '18')
        self.assertEqual(clean_piece('11-13'), '11-13')
        self.assertEqual(clean_piece('x' * 20), 'x' * 20)
        proforma = draft([line(piece='  36 '), line(piece='')])
        self.assertEqual([l.dental_piece for l in proforma.lines], ['36', ''])

    def test_invalid_piece_is_rejected_on_that_line(self):  # AC-02
        for bad in ('x' * 21, '1\n2', 'a\rb', 12):
            with self.assertRaises(DentalProformaValidationError) as ctx:
                draft([line(), line(piece=bad)])
            self.assertEqual(ctx.exception.errors['lines'][0], {})
            self.assertIn('dental_piece', ctx.exception.errors['lines'][1])

    def test_present_requires_lines_and_freezes(self):  # AC-05
        with self.assertRaises(DentalProformaValidationError):
            draft().present()
        proforma = draft([line()])
        proforma.present()
        self.assertEqual(proforma.status, PRESENTED)
        with self.assertRaises(DentalProformaStateError):
            proforma.replace_content(patient_name='A', date=proforma.date, valid_until=None, notes='', lines=[])
        with self.assertRaises(DentalProformaStateError):
            proforma.present()

    def test_new_version_keeps_frozen_lines_and_pieces(self):  # AC-05 / AC-02 / INV-06
        original = draft([line(price='100', piece='18')])
        with self.assertRaises(DentalProformaStateError):
            original.new_version()
        original.present()
        nxt = original.new_version()
        self.assertEqual((nxt.number, nxt.version, nxt.status), (original.number, 2, DRAFT))
        self.assertEqual([(l.description, l.unit_price, l.dental_piece) for l in nxt.lines],
                         [(l.description, l.unit_price, l.dental_piece) for l in original.lines])
        self.assertNotEqual(nxt.lines[0].id, original.lines[0].id)
        original.supersede()
        self.assertEqual(original.status, SUPERSEDED)
        with self.assertRaises(DentalProformaStateError):
            original.supersede()
