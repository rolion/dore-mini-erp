import io
from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from modules.data_import.domain.errors import ImportValidationError
from modules.data_import.domain.fields import parse_options, suggest_mapping, validate_mapping
from modules.data_import.domain.normalize import (
    ValueProblem,
    normalize_name,
    parse_date,
    parse_decimal,
    parse_payment_method,
    parse_quantity,
)
from modules.data_import.domain.sales_rows import parse_sales
from modules.data_import.infrastructure.file_parsers import MAX_ROWS, TEMPLATE_CSV, parse_upload

HEADERS = ['Fecha', 'Producto', 'Cantidad', 'Precio', 'Nro Venta', 'Cliente', 'Método de pago']
TODAY = date(2026, 11, 19)


def _parse(rows, **opts):
    mapping = validate_mapping(suggest_mapping(HEADERS), HEADERS)
    return parse_sales(HEADERS, rows, mapping, parse_options(opts), TODAY)


class NormalizeTests(SimpleTestCase):
    def test_names_ignore_case_accents_and_spaces(self):
        self.assertEqual(normalize_name('  Café   MOLIDO '), 'cafe molido')

    def test_decimals(self):
        for raw, expected in [('12,50', '12.50'), ('1.234,50', '1234.50'), ('1,234.50', '1234.50'),
                              ('1,234', '1234'), ('Bs 12.5', '12.5')]:
            self.assertEqual(parse_decimal(raw), Decimal(expected), raw)

    def test_dates_and_formats(self):
        self.assertEqual(parse_date('05/02/2026'), date(2026, 2, 5))
        self.assertEqual(parse_date('05/02/2026', 'mdy'), date(2026, 5, 2))
        self.assertEqual(parse_date('2026-02-05'), date(2026, 2, 5))
        with self.assertRaises(ValueProblem):
            parse_date('31/02/2026')

    def test_textual_dates_without_year(self):
        today = date(2026, 11, 20)
        self.assertEqual(parse_date('3 ago.', today=today), date(2026, 8, 3))
        self.assertEqual(parse_date('4 sep.', today=today), date(2026, 9, 4))
        self.assertEqual(parse_date('3 de agosto de 2025', today=today), date(2025, 8, 3))
        self.assertEqual(parse_date('15 dic', today=today), date(2025, 12, 15))
        with self.assertRaises(ValueProblem):
            parse_date('31 feb.', today=today)

    def test_quantity_must_be_positive_integer(self):
        self.assertEqual(parse_quantity('3'), 3)
        for bad in ('0', '-1', '1,5', 'x', '100001'):
            with self.assertRaises(ValueProblem):
                parse_quantity(bad)

    def test_payment_synonyms(self):
        self.assertEqual(parse_payment_method('Efectivo'), 'CASH')
        self.assertEqual(parse_payment_method('transferencia'), 'BANK_TRANSFER')
        with self.assertRaises(ValueProblem):
            parse_payment_method('trueque')


class MappingTests(SimpleTestCase):
    def test_suggestion_and_required(self):
        mapping = suggest_mapping(HEADERS)
        self.assertEqual(mapping['sale_date'], 'Fecha')
        self.assertEqual(mapping['payment_method'], 'Método de pago')
        with self.assertRaises(ImportValidationError) as ctx:
            validate_mapping({**mapping, 'quantity': None}, HEADERS)
        self.assertIn('mapping.quantity', ctx.exception.errors)

    def test_unknown_column_rejected(self):
        with self.assertRaises(ImportValidationError):
            validate_mapping({**suggest_mapping(HEADERS), 'product_name': 'Nope'}, HEADERS)

    def test_options_defaults_and_validation(self):
        options = parse_options({})
        self.assertEqual((options.default_payment_method, options.default_sales_channel), ('CASH', 'OTHER'))
        with self.assertRaises(ImportValidationError):
            parse_options({'infer_products': 'si'})


class SalesRowsTests(SimpleTestCase):
    def test_groups_by_sale_number_and_totals(self):
        parsed = _parse([['01/02/2026', 'Café', '2', '10,50', 'A1', 'Ana', 'efectivo'],
                         ['01/02/2026', 'Té', '1', '5', 'A1', 'Ana', 'efectivo']])
        self.assertEqual(len(parsed.groups), 1)
        self.assertEqual(parsed.groups[0].total, Decimal('26.00'))
        self.assertEqual(parsed.groups[0].key, 'n:a1')

    def test_discount_is_taken_from_the_sale_and_lowers_the_total(self):
        headers = HEADERS + ['Descuento']
        mapping = validate_mapping(suggest_mapping(headers), headers)
        rows = [['01/02/2026', 'Café', '2', '10', 'A1', 'Ana', '', '5'],
                ['01/02/2026', 'Té', '1', '5', 'A1', 'Ana', '', ''],
                ['01/02/2026', 'Café', '1', '10', 'A2', 'Ana', '', '50']]
        parsed = parse_sales(headers, rows, mapping, parse_options({}), TODAY)
        self.assertEqual(parsed.groups[0].discount, Decimal('5.00'))
        self.assertEqual(parsed.groups[0].total, Decimal('20.00'))
        self.assertEqual(parsed.problems[0].code, 'discount_exceeds_subtotal')

    def test_row_errors_invalidate_only_their_sale(self):
        parsed = _parse([['01/02/2026', 'Café', '2', '10', 'A1', '', ''], ['01/02/2026', 'Té', 'x', '5', 'A2', '', '']])
        self.assertEqual(len(parsed.groups), 1)
        self.assertEqual(parsed.invalid_sales, 1)
        self.assertEqual(parsed.problems[0].field, 'quantity')

    def test_future_date_and_inconsistent_lines(self):
        parsed = _parse([['01/01/2027', 'Café', '1', '1', 'F', '', '']])
        self.assertEqual(parsed.problems[0].code, 'future_date')
        parsed = _parse([['01/02/2026', 'Café', '1', '1', 'B', 'Ana', ''],
                         ['02/02/2026', 'Té', '1', '1', 'B', 'Ana', '']])
        self.assertEqual(parsed.problems[0].code, 'sale_inconsistent')

    def test_hash_keys_stable_and_occurrence_counted(self):
        row = ['01/02/2026', 'Café', '1', '3', '', '', '']
        first = _parse([row, row]).groups
        self.assertEqual(len({g.key for g in first}), 2)
        self.assertEqual({g.key for g in first}, {g.key for g in _parse([row, row]).groups})

    def test_default_method_does_not_change_key(self):
        row = [['01/02/2026', 'Café', '1', '3', '', '', '']]
        mapping = validate_mapping(suggest_mapping(HEADERS), HEADERS)
        a = parse_sales(HEADERS, row, mapping, parse_options({'default_payment_method': 'CASH'}), TODAY)
        b = parse_sales(HEADERS, row, mapping, parse_options({'default_payment_method': 'QR'}), TODAY)
        self.assertEqual(a.groups[0].key, b.groups[0].key)


class ParserTests(SimpleTestCase):
    def test_csv_template(self):
        parsed = parse_upload('plantilla.csv', TEMPLATE_CSV.encode())
        self.assertEqual(len(parsed.rows), 3)

    def test_semicolon_and_latin1(self):
        parsed = parse_upload('a.csv', 'Fecha;Producto\n01/02/2026;Café\n'.encode('cp1252'))
        self.assertEqual(parsed.rows[0][1], 'Café')

    def test_rejections(self):
        for name, content in [('a.txt', b'x'), ('a.csv', b''), ('a.csv', b'A,A\n1,2\n'), ('a.xlsx', b'nope'),
                              ('a.csv', b'A,B\n')]:
            with self.assertRaises(ImportValidationError, msg=name):
                parse_upload(name, content)
        big = 'A,B\n' + '1,2\n' * (MAX_ROWS + 1)
        with self.assertRaises(ImportValidationError):
            parse_upload('a.csv', big.encode())

    def test_xlsx(self):
        import openpyxl
        book = openpyxl.Workbook()
        book.active.append(['Fecha', 'Producto'])
        book.active.append([date(2026, 2, 5), 'Café'])
        buffer = io.BytesIO()
        book.save(buffer)
        parsed = parse_upload('a.xlsx', buffer.getvalue())
        self.assertEqual(parsed.rows, [['2026-02-05', 'Café']])
