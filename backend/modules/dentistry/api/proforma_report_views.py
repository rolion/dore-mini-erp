"""Reportes de proformas odontológicas: lista paginada con totales y exportación a Excel y PDF."""
from datetime import date

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from config.permissions import CompanyClinicalPermission
from modules.dentistry.application.proforma_reports import PAID, RECEIVABLE, ProformaReports
from modules.dentistry.infrastructure.adapters import CollectionsReader, ProfessionalLookup
from modules.dentistry.infrastructure.proforma_repository import DjangoDentalProformaRepository
from shared.report_export import (
    MAX_EXPORT_ROWS, PDF_CONTENT_TYPE, XLSX_CONTENT_TYPE, build_table_pdf, build_table_xlsx,
)
from shared.tenancy import company_id_from

from .proforma_views import ProformaPagination

REQUIRED_MODULES = ('dentistry', 'receivables')
NO_DOCTOR = '—'
MONEY_COLUMNS = (3,)

REPORTS = {
    RECEIVABLE: {'title': 'Proformas por cobrar', 'slug': 'proformas-por-cobrar', 'amount': 'Saldo por cobrar',
                 'everything': 'Todas las proformas con saldo por cobrar'},
    PAID: {'title': 'Proformas pagadas', 'slug': 'proformas-pagadas', 'amount': 'Total cobrado',
           'everything': 'Todas las proformas pagadas'},
}


def _date(request, name: str) -> date | None:
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValidationError({name: ['Fecha inválida: use el formato AAAA-MM-DD.']}) from None


def _filters(request) -> tuple[date | None, date | None]:
    date_from, date_to = _date(request, 'date_from'), _date(request, 'date_to')
    if date_from and date_to and date_from > date_to:
        raise ValidationError({'date_to': ['La fecha final no puede ser anterior a la inicial.']})
    return date_from, date_to


def _report(request, kind: str):
    company_id = company_id_from(request)
    use_case = ProformaReports(DjangoDentalProformaRepository(company_id), CollectionsReader(company_id),
                               ProfessionalLookup(company_id))
    return use_case.execute(kind, *_filters(request))


def _row(row) -> dict:
    return {'id': str(row.id), 'code': row.number, 'order_date': row.date.isoformat(),
            'customer': {'id': str(row.patient_id), 'name': row.patient_name},
            'doctor': {'id': str(row.professional_id), 'name': row.professional_name} if row.professional_id else None,
            'amount': f'{row.amount:.2f}'}


class _ReportView(APIView):
    required_modules = REQUIRED_MODULES
    permission_classes = [CompanyClinicalPermission]
    kind = ''

    def get(self, request):
        report = _report(request, self.kind)
        paginator = ProformaPagination()
        page = paginator.paginate_queryset(report.rows, request, view=self)
        response = paginator.get_paginated_response([_row(row) for row in page])
        response.data['totals'] = {'count': report.count, 'amount': f'{report.total:.2f}'}
        return response


class _ReportExportView(APIView):
    required_modules = REQUIRED_MODULES
    permission_classes = [CompanyClinicalPermission]
    kind = ''

    def get(self, request, file_format):
        if file_format not in ('xlsx', 'pdf'):
            raise NotFound('Formato no disponible.')
        date_from, date_to = _filters(request)
        report = _report(request, self.kind)
        if report.count > MAX_EXPORT_ROWS:
            raise ValidationError({'detail': [
                f'El reporte tiene más de {MAX_EXPORT_ROWS} proformas: acote el rango de fechas.']})
        config = REPORTS[self.kind]
        headers = ('Proforma', 'Paciente', 'Doctor', config['amount'])
        rows = [(r.number, r.patient_name, r.professional_name or NO_DOCTOR, r.amount)
                for r in report.rows]
        footer = ('Totales', f'{report.count} proformas', '', report.total)
        today = timezone.localdate()
        if file_format == 'xlsx':
            content = build_table_xlsx(config['title'], headers, rows, footer, MONEY_COLUMNS, (18, 34, 30, 18))
            content_type = XLSX_CONTENT_TYPE
        else:
            parts = ([f'Desde {date_from.strftime("%d/%m/%Y")}'] if date_from else []) + (
                [f'Hasta {date_to.strftime("%d/%m/%Y")}'] if date_to else [])
            content = build_table_pdf(config['title'], ' · '.join(parts) or config['everything'], today, headers,
                                      rows, footer, MONEY_COLUMNS, (80, 170, 170, 103))
            content_type = PDF_CONTENT_TYPE
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{config["slug"]}-{today.isoformat()}.{file_format}"'
        return response


class ReceivableProformasReportView(_ReportView):
    kind = RECEIVABLE


class ReceivableProformasReportExportView(_ReportExportView):
    kind = RECEIVABLE


class PaidProformasReportView(_ReportView):
    kind = PAID


class PaidProformasReportExportView(_ReportExportView):
    kind = PAID
