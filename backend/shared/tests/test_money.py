from decimal import Decimal

from django.test import SimpleTestCase

from shared.domain.money import DECIMALS, MONEY_MAX, NEGATIVE, TOO_LARGE, TYPE, InvalidMoney, parse_money


class ParseMoneyTests(SimpleTestCase):
    def test_valid_values_are_normalized_to_two_decimals(self):  # INV-01
        self.assertEqual(parse_money('35'), Decimal('35.00'))
        self.assertEqual(parse_money(' 12.5 '), Decimal('12.50'))
        self.assertEqual(parse_money(7), Decimal('7.00'))
        self.assertEqual(parse_money(Decimal('0')), Decimal('0.00'))
        self.assertEqual(parse_money(MONEY_MAX), MONEY_MAX)

    def assertInvalid(self, value, code):
        with self.assertRaises(InvalidMoney) as ctx:
            parse_money(value)
        self.assertEqual(ctx.exception.code, code)

    def test_float_and_bool_are_rejected(self):  # INV-01
        self.assertInvalid(1.5, TYPE)
        self.assertInvalid(True, TYPE)
        self.assertInvalid(None, TYPE)

    def test_non_numeric_text_and_non_finite_values_are_rejected(self):
        self.assertInvalid('abc', TYPE)
        self.assertInvalid('', TYPE)
        self.assertInvalid('NaN', TYPE)
        self.assertInvalid('Infinity', TYPE)

    def test_negative_extra_decimals_and_overflow_are_rejected(self):
        self.assertInvalid('-0.01', NEGATIVE)
        self.assertInvalid('1.005', DECIMALS)
        self.assertInvalid(Decimal('10000000000.00'), TOO_LARGE)
