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


def build_xlsx(rows, totals, title: str = TITLE, headers: tuple[str, ...] = HEADERS,
               count_label: str = 'pedidos') -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for code, customer, total, balance in rows:
        sheet.append([code, customer, total, balance])
    sheet.append(['Totales', f'{totals.orders_count} {count_label}', totals.total, totals.balance])
    for cell in sheet[sheet.max_row]:
        cell.font = Font(bold=True)
    for row in sheet.iter_rows(min_row=2, max_col=2):
        for cell in row:  # un texto que empieza por «=» (p. ej. un nombre de cliente) nunca debe ser una fórmula
            if isinstance(cell.value, str) and cell.value.startswith('='):
                cell.data_type = 's'
    for row in sheet.iter_rows(min_row=2, min_col=3, max_col=4):
        for cell in row:
            cell.number_format = '#,##0.00'
            cell.alignment = Alignment(horizontal='right')
    for column, width in zip('ABCD', (18, 36, 16, 16)):
        sheet.column_dimensions[column].width = width
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_pdf(rows, totals, filters_text: str, generated_on: date, title: str = TITLE,
              headers: tuple[str, ...] = HEADERS, count_label: str = 'pedidos') -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title=title, leftMargin=36, rightMargin=36,
                                 topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [Paragraph(escape(title), styles['Title']),
             Paragraph(f'{filters_text} · Generado el {generated_on.strftime("%d/%m/%Y")}', styles['Normal']),
             Spacer(1, 12)]
    data = [list(headers)]
    data += [[code, Paragraph(escape(customer), styles['Normal']), _money(total), _money(balance)]
             for code, customer, total, balance in rows]
    data.append(['Totales', f'{totals.orders_count} {count_label}', _money(totals.total), _money(totals.balance)])
    table = Table(data, colWidths=[110, 230, 90, 90], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#adb5bd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(table)
    document.build(story)
    return buffer.getvalue()
