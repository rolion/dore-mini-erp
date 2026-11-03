from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.quotations.domain.proforma import (
    DRAFT, PRESENTED, SUPERSEDED, Proforma, ProformaLine, ProformaStateError, ProformaValidationError,
)


def line(quantity='1', price='100', **extra):
    return ProformaLine(uuid4(), uuid4(), 'Consulta', Decimal(quantity), Decimal(price), **extra)


def draft(lines=()):
    return Proforma.create(number='PRO-000001', customer_id=uuid4(), customer_name='Ana',
                           date=date(2026, 11, 3), lines=lines)


class ProformaDomainTests(SimpleTestCase):
    def test_total_of_two_services(self):  # AC-01 / INV-01
        self.assertEqual(draft([line(price='100'), line(price='150')]).total, Decimal('250.00'))

    def test_subtotal_rounds_half_up_to_two_decimals(self):  # INV-01
        self.assertEqual(line(quantity='1.50', price='0.15').subtotal, Decimal('0.23'))
        self.assertEqual(draft([line(quantity='3', price='0.10')]).total, Decimal('0.30'))

    def test_invalid_quantity_and_price_report_errors_per_line(self):  # AC-02
        for quantity, price in (('0', '1'), ('-1', '1'), ('1', '-0.01'), ('1.001', '1'), ('10000', '1')):
            with self.assertRaises(ProformaValidationError) as ctx:
                draft([line(), line(quantity, price)])
            errors = ctx.exception.errors['lines']
            self.assertEqual(errors[0], {})
            self.assertTrue(errors[1])

    def test_zero_price_is_allowed(self):
        self.assertEqual(draft([line(price='0')]).total, Decimal('0.00'))

    def test_valid_until_cannot_precede_date(self):
        with self.assertRaises(ProformaValidationError):
            Proforma.create(number='X', customer_id=uuid4(), customer_name='A', date=date(2026, 11, 3),
                            valid_until=date(2026, 11, 2))

    def test_present_requires_lines_and_freezes(self):  # AC-05 / INV-03
        empty = draft()
        with self.assertRaises(ProformaValidationError):
            empty.present()
        proforma = draft([line()])
        proforma.present()
        self.assertEqual(proforma.status, PRESENTED)
        with self.assertRaises(ProformaStateError):
            proforma.replace_content(customer_id=proforma.customer_id, customer_name='A', date=proforma.date,
                                     valid_until=None, notes='', lines=[])
        with self.assertRaises(ProformaStateError):
            proforma.present()

    def test_new_version_copies_frozen_lines_and_supersede(self):  # AC-08 / INV-05
        original = draft([line(price='100')])
        with self.assertRaises(ProformaStateError):
            original.new_version()
        original.present()
        nxt = original.new_version()
        self.assertEqual((nxt.number, nxt.version, nxt.status), (original.number, 2, DRAFT))
        self.assertEqual([(l.description, l.unit_price) for l in nxt.lines],
                         [(l.description, l.unit_price) for l in original.lines])
        self.assertNotEqual(nxt.lines[0].id, original.lines[0].id)
        original.supersede()
        self.assertEqual(original.status, SUPERSEDED)
        with self.assertRaises(ProformaStateError):
            original.supersede()
