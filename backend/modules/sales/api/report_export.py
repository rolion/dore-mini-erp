"""Exportación del reporte «Ingresos por venta» a Excel y PDF (mismas columnas y totales que la pantalla)."""
from datetime import date
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

TITLE = 'Ingresos por venta'
HEADERS = ('Pedido', 'Cliente', 'Total', 'Saldo')
NO_CUSTOMER = '—'
XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
PDF_CONTENT_TYPE = 'application/pdf'
MAX_EXPORT_ROWS = 5000


def report_rows(summaries, customer_names: dict, customers_available: bool) -> list[tuple[str, str, Decimal, Decimal]]:
    rows = []
    for order in summaries:
        name = customer_names.get(order.customer_id, '') if customers_available and order.customer_id else ''
        rows.append((order.code, name or NO_CUSTOMER, order.total, order.balance))
    return rows


def _money(value: Decimal) -> str:
    return f'{value:,.2f}'


def build_xlsx(rows, totals) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = TITLE
    sheet.append(HEADERS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for code, customer, total, balance in rows:
        sheet.append([code, customer, total, balance])
    sheet.append(['Totales', f'{totals.orders_count} pedidos', totals.total, totals.balance])
    for cell in sheet[sheet.max_row]:
        cell.font = Font(bold=True)
    for row in sheet.iter_rows(min_row=2, min_col=3, max_col=4):
        for cell in row:
            cell.number_format = '#,##0.00'
            cell.alignment = Alignment(horizontal='right')
    for column, width in zip('ABCD', (18, 36, 16, 16)):
        sheet.column_dimensions[column].width = width
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_pdf(rows, totals, filters_text: str, generated_on: date) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title=TITLE, leftMargin=36, rightMargin=36,
                                 topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [Paragraph(TITLE, styles['Title']),
             Paragraph(f'{filters_text} · Generado el {generated_on.strftime("%d/%m/%Y")}', styles['Normal']),
             Spacer(1, 12)]
    data = [list(HEADERS)]
    data += [[code, Paragraph(customer, styles['Normal']), _money(total), _money(balance)]
             for code, customer, total, balance in rows]
    data.append(['Totales', f'{totals.orders_count} pedidos', _money(totals.total), _money(totals.balance)])
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
