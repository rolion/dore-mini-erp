"""Reportes «Compras pagadas» y «Compras por pagar»: solo lectura, paginados, con totales y exportación."""
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from modules.purchases.application.purchase_report_queries import PaidPurchasesReport, PayablePurchasesReport
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository
from shared.report_export import (
    MAX_EXPORT_ROWS,
    PDF_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    ReportTotals,
    build_pdf,
    build_xlsx,
    report_rows,
)
from shared.tenancy import company_id_from

from .pagination import SupplierPagination
from .purchase_filters import parse_purchase_filters
from .purchase_serializers import money

REQUIRED_MODULES = ('purchases',)
HEADERS = ('Compra', 'Proveedor', 'Total', 'Saldo')


def _filters(request):
    """Solo fechas y período fiscal: el estado y el pago los fija cada reporte (no son filtros de la persona)."""
    return parse_purchase_filters({key: request.query_params.get(key) for key in
                                   ('date_from', 'date_to', 'fiscal_period_id')})


def _report(request, use_case):
    return use_case(DjangoPurchaseRepository(company_id_from(request))).execute(_filters(request))


def _row(summary) -> dict:
    """Misma forma que las filas de los reportes de ventas, para compartir la pantalla del frontend."""
    return {
        'id': summary.id, 'code': summary.reference, 'order_date': summary.purchase_date.isoformat(),
        'customer': {'id': summary.supplier_id, 'name': summary.supplier_name},
        'total': money(summary.total), 'balance': money(summary.balance),
    }


def _totals(totals) -> dict:
    return {'orders_count': totals.purchases_count, 'total': money(totals.total), 'balance': money(totals.balance)}


class _PurchasesReportView(APIView):
    required_modules = REQUIRED_MODULES
    use_case = None

    def get(self, request):
        report = _report(request, self.use_case)
        paginator = SupplierPagination()
        page = paginator.paginate_queryset(report.purchases, request, view=self)
        response = paginator.get_paginated_response([_row(summary) for summary in page])
        response.data['totals'] = _totals(report.totals)
        return response


class _PurchasesReportExportView(APIView):
    required_modules = REQUIRED_MODULES
    use_case = None
    title = ''
    file_slug = ''
    everything_text = ''

    def get(self, request, file_format):
        if file_format not in ('xlsx', 'pdf'):
            raise NotFound('Formato no disponible.')
        filters = _filters(request)
        report = _report(request, self.use_case)
        if report.totals.purchases_count > MAX_EXPORT_ROWS:
            raise ValidationError({'detail': [
                f'El reporte tiene más de {MAX_EXPORT_ROWS} compras: acote las fechas o el período fiscal.']})
        rows = report_rows([(p.reference, p.supplier_id, p.total, p.balance) for p in report.purchases],
                           {p.supplier_id: p.supplier_name for p in report.purchases}, True)
        totals = ReportTotals(report.totals.purchases_count, report.totals.total, report.totals.balance)
        today = timezone.localdate()
        if file_format == 'xlsx':
            content, content_type = build_xlsx(rows, totals, self.title, HEADERS, 'compras'), XLSX_CONTENT_TYPE
        else:
            content, content_type = (build_pdf(rows, totals, _filters_text(filters, self.everything_text), today,
                                               self.title, HEADERS, 'compras'), PDF_CONTENT_TYPE)
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{self.file_slug}-{today.isoformat()}.{file_format}"'
        return response


def _filters_text(filters, everything_text: str) -> str:
    parts = []
    if filters.date_from:
        parts.append(f'Desde {filters.date_from.strftime("%d/%m/%Y")}')
    if filters.date_to:
        parts.append(f'Hasta {filters.date_to.strftime("%d/%m/%Y")}')
    if filters.fiscal_period_id:
        parts.append('Período fiscal seleccionado')
    return ' · '.join(parts) or everything_text


class PaidPurchasesReportView(_PurchasesReportView):
    use_case = PaidPurchasesReport


class PaidPurchasesReportExportView(_PurchasesReportExportView):
    use_case = PaidPurchasesReport
    title = 'Compras pagadas'
    file_slug = 'compras-pagadas'
    everything_text = 'Todas las compras pagadas hasta la fecha'


class PayablePurchasesReportView(_PurchasesReportView):
    use_case = PayablePurchasesReport


class PayablePurchasesReportExportView(_PurchasesReportExportView):
    use_case = PayablePurchasesReport
    title = 'Compras por pagar'
    file_slug = 'compras-por-pagar'
    everything_text = 'Todas las compras con saldo pendiente hasta la fecha'
