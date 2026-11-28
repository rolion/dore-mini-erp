"""Exportación de los reportes de documentos (ventas y compras) a Excel y PDF, con las columnas de la pantalla."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

TITLE = 'Reporte'
HEADERS = ('Documento', 'Tercero', 'Total', 'Saldo')
NO_CUSTOMER = '—'
XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
PDF_CONTENT_TYPE = 'application/pdf'
MAX_EXPORT_ROWS = 5000


@dataclass(frozen=True)
class ReportTotals:
    """Pie de los archivos: cantidad de documentos y sumas de total y saldo del conjunto filtrado."""

    orders_count: int
    total: Decimal
    balance: Decimal


def report_rows(entries, names: dict, names_available: bool) -> list[tuple[str, str, Decimal, Decimal]]:
    """Filas `(código, nombre del tercero, total, saldo)` desde `(código, id del tercero, total, saldo)`."""
    rows = []
    for code, party_id, total, balance in entries:
        name = names.get(party_id, '') if names_available and party_id else ''
        rows.append((code, name or NO_CUSTOMER, total, balance))
    return rows


def _money(value: Decimal) -> str:
    return f'{value:,.2f}'


def build_table_xlsx(title: str, headers: tuple[str, ...], rows, footer, money_columns: tuple[int, ...],
                     widths: tuple[int, ...]) -> bytes:
    """Excel genérico: encabezados, filas y un pie en negrita; `money_columns` (0-based) con formato de dinero."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        sheet.append(list(row))
    sheet.append(list(footer))
    for cell in sheet[sheet.max_row]:
        cell.font = Font(bold=True)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith('='):
                cell.data_type = 's'  # un texto que empieza por «=» (p. ej. un nombre) nunca debe ser una fórmula
            if cell.column - 1 in money_columns:
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right')
    for index, width in enumerate(widths):
        sheet.column_dimensions[chr(ord('A') + index)].width = width
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_table_pdf(title: str, filters_text: str, generated_on: date, headers: tuple[str, ...], rows, footer,
                    money_columns: tuple[int, ...], col_widths: tuple[int, ...]) -> bytes:
    """PDF genérico con la misma estructura que `build_table_xlsx`."""
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title=title, leftMargin=36, rightMargin=36,
                                 topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [Paragraph(escape(title), styles['Title']),
             Paragraph(f'{escape(filters_text)} · Generado el {generated_on.strftime("%d/%m/%Y")}', styles['Normal']),
             Spacer(1, 12)]

    def cell(index: int, value):
        if index in money_columns and isinstance(value, Decimal):
            return _money(value)
        return Paragraph(escape(str(value)), styles['Normal']) if index else str(value)

    data = [list(headers)]
    data += [[cell(index, value) for index, value in enumerate(row)] for row in rows]
    data.append([_money(v) if i in money_columns and isinstance(v, Decimal) else v for i, v in enumerate(footer)])
    table = Table(data, colWidths=list(col_widths), repeatRows=1)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#adb5bd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    style += [('ALIGN', (c, 0), (c, -1), 'RIGHT') for c in money_columns]
    table.setStyle(TableStyle(style))
    story.append(table)
    document.build(story)
    return buffer.getvalue()


def build_xlsx(rows, totals, title: str = TITLE, headers: tuple[str, ...] = HEADERS,
               count_label: str = 'pedidos') -> bytes:
    footer = ('Totales', f'{totals.orders_count} {count_label}', totals.total, totals.balance)
    return build_table_xlsx(title, headers, rows, footer, (2, 3), (18, 36, 16, 16))


def build_pdf(rows, totals, filters_text: str, generated_on: date, title: str = TITLE,
              headers: tuple[str, ...] = HEADERS, count_label: str = 'pedidos') -> bytes:
    footer = ('Totales', f'{totals.orders_count} {count_label}', totals.total, totals.balance)
    return build_table_pdf(title, filters_text, generated_on, headers, rows, footer, (2, 3), (110, 230, 90, 90))
