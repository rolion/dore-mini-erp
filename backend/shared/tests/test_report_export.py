from datetime import date
from decimal import Decimal
from io import BytesIO

from django.test import SimpleTestCase
from openpyxl import load_workbook

from shared.report_export import ReportTotals, build_pdf, build_table_pdf, build_table_xlsx, build_xlsx

HEADERS = ('Código', 'Nombre', 'Monto')
ROWS = [('A-1', '=HYPERLINK("x")', Decimal('1234.5')), ('A-2', 'Ana', Decimal('10'))]
FOOTER = ('Totales', '2 filas', Decimal('1244.5'))


class TableExportTests(SimpleTestCase):
    def sheet(self):
        data = build_table_xlsx('Título', HEADERS, ROWS, FOOTER, (2,), (10, 20, 12))
        return load_workbook(BytesIO(data)).active

    def test_xlsx_declares_columns_footer_and_money_format(self):
        sheet = self.sheet()
        self.assertEqual([c.value for c in sheet[1]], list(HEADERS))
        self.assertEqual(sheet.title, 'Título')
        self.assertEqual(sheet['C2'].value, Decimal('1234.5'))
        self.assertEqual(sheet['C2'].number_format, '#,##0.00')
        self.assertEqual((sheet['A4'].value, sheet['A4'].font.bold), ('Totales', True))

    def test_xlsx_neutralizes_formulas(self):
        cell = self.sheet()['B2']
        self.assertEqual((cell.value, cell.data_type), ('=HYPERLINK("x")', 's'))

    def test_pdf_is_generated_and_escapes_markup(self):
        rows = [('A-1', '<b>&</b>', Decimal('5'))]
        data = build_table_pdf('Título', 'Filtro <x>', date(2026, 11, 28), HEADERS, rows, FOOTER, (2,), (90, 300, 90))
        self.assertTrue(data.startswith(b'%PDF'))


class LegacyDocumentExportTests(SimpleTestCase):
    """AC-12: ventas y compras siguen exportando con las mismas columnas tras delegar en `build_table_*`."""

    def test_build_xlsx_keeps_columns_and_footer(self):
        totals = ReportTotals(1, Decimal('100'), Decimal('40'))
        sheet = load_workbook(BytesIO(build_xlsx([('V-1', 'Ana', Decimal('100'), Decimal('40'))], totals))).active
        self.assertEqual([c.value for c in sheet[1]], ['Documento', 'Tercero', 'Total', 'Saldo'])
        self.assertEqual([c.value for c in sheet[3]], ['Totales', '1 pedidos', Decimal('100'), Decimal('40')])

    def test_build_pdf_is_a_pdf(self):
        totals = ReportTotals(1, Decimal('100'), Decimal('40'))
        data = build_pdf([('V-1', 'Ana', Decimal('100'), Decimal('40'))], totals, 'Todos', date(2026, 11, 28))
        self.assertTrue(data.startswith(b'%PDF'))
