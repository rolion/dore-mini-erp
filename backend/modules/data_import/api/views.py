from uuid import UUID

from django.http import HttpResponse
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.data_import.application.ports import RunData
from modules.data_import.application.use_cases import ExecuteSalesImport, PreviewSalesImport, UploadSalesFile
from modules.data_import.domain.errors import ImportNotFound, ImportRuleViolation, ImportValidationError
from modules.data_import.infrastructure.adapters import SalesImportAdapter, SystemClock
from modules.data_import.infrastructure.django.repositories import DjangoImportRepository
from modules.data_import.infrastructure.file_parsers import TEMPLATE_CSV, parse_upload
from shared.tenancy import company_id_from

from .pagination import ImportPagination

REQUIRED_MODULES = ('sales', 'catalog')
RUN_NOT_FOUND = 'Importación no encontrada.'


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT


def _uuid(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError:
        raise NotFound(RUN_NOT_FOUND) from None


def _repository(request) -> DjangoImportRepository:
    """Repositorio de la empresa del usuario autenticado (nunca de un dato enviado por el cliente)."""
    return DjangoImportRepository(company_id_from(request))


def _user_name(request) -> str:
    user = request.user
    return user.get_full_name().strip() or user.get_username()


def _gateway(request) -> SalesImportAdapter:
    return SalesImportAdapter(company_id_from(request), request.user.pk, _user_name(request))


def _run(callable_, **kwargs):
    """Traduce los errores del dominio de la importación a HTTP."""
    try:
        return callable_(**kwargs)
    except ImportValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except ImportRuleViolation as exc:
        raise Conflict({'code': exc.code, 'detail': exc.message}) from exc
    except ImportNotFound as exc:
        raise NotFound(RUN_NOT_FOUND) from exc


def _capabilities(caps) -> dict:
    return {
        'customers': caps.customers, 'inventory': caps.inventory, 'purchases': caps.purchases,
        'accounting': caps.accounting, 'costing': caps.costing,
        'warehouses': [{'id': str(w.id), 'name': w.name, 'is_default': w.is_default} for w in caps.warehouses],
        'payment_methods': ['CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'],
        'sales_channels': ['WHATSAPP', 'FACEBOOK', 'INSTAGRAM', 'STORE', 'FAIR', 'OTHER'],
    }


def _summary(run: RunData) -> dict:
    return {'id': str(run.id), 'filename': run.filename, 'status': run.status, 'created_at': run.created_at,
            'created_by_name': run.created_by_name, 'row_count': run.row_count, 'counts': run.counts}


def _model_summary(model) -> dict:
    return {'id': str(model.id), 'filename': model.filename, 'status': model.status, 'created_at': model.created_at,
            'created_by_name': model.created_by_name, 'row_count': model.row_count, 'counts': model.counts}


class RunListCreateView(APIView):
    required_modules = REQUIRED_MODULES
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        paginator = ImportPagination()
        page = paginator.paginate_queryset(_repository(request).list_runs(), request, view=self)
        return paginator.get_paginated_response([_model_summary(m) for m in page])

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            raise ValidationError({'file': ['Selecciona un archivo .csv o .xlsx.']})
        content = upload.read(5 * 1024 * 1024 + 1)
        use_case = UploadSalesFile(_repository(request), _gateway(request), parse_upload)
        result = _run(use_case.execute, filename=upload.name, content=content, user_id=request.user.pk,
                      user_name=_user_name(request))
        run = result.run
        return Response({
            **_summary(run), 'headers': run.headers, 'sample_rows': run.rows[:5],
            'suggested_mapping': result.suggested_mapping, 'capabilities': _capabilities(result.capabilities),
        }, status=status.HTTP_201_CREATED)


class RunDetailView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request, run_id):
        run = _repository(request).get_run(_uuid(run_id))
        if run is None:
            raise NotFound(RUN_NOT_FOUND)
        return Response({**_summary(run), 'options': run.options, 'mapping': run.mapping})


class RunPreviewView(APIView):
    required_modules = REQUIRED_MODULES

    def post(self, request, run_id):
        use_case = PreviewSalesImport(_repository(request), _gateway(request), SystemClock())
        result = _run(use_case.execute, run_id=_uuid(run_id), mapping=request.data.get('mapping'),
                      options=request.data.get('options'))
        return Response(result.as_dict())


class RunExecuteView(APIView):
    required_modules = REQUIRED_MODULES

    def post(self, request, run_id):
        raw_key = request.data.get('idempotency_key')
        key = None
        if raw_key not in (None, ''):
            try:
                key = UUID(str(raw_key))
            except ValueError:
                raise ValidationError({'idempotency_key': ['La clave de la operación no es válida.']}) from None
        use_case = ExecuteSalesImport(_repository(request), _gateway(request), SystemClock())
        run = _run(use_case.execute, run_id=_uuid(run_id), mapping=request.data.get('mapping'),
                   options=request.data.get('options'), idempotency_key=key)
        return Response({'id': str(run.id), 'status': run.status, 'counts': run.counts,
                         'rows_url': f'/api/imports/sales/{run.id}/rows/'})


class RunRowsView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request, run_id):
        repository = _repository(request)
        run_uuid = _uuid(run_id)
        if repository.get_run(run_uuid) is None:
            raise NotFound(RUN_NOT_FOUND)
        results = repository.list_results(run_uuid, request.query_params.get('status') or None)
        paginator = ImportPagination()
        page = paginator.paginate_queryset(results, request, view=self)
        return paginator.get_paginated_response([{
            'row': r.row_number, 'sale_key': r.sale_key, 'status': r.status, 'code': r.code, 'message': r.message,
            'order_id': str(r.order_id) if r.order_id else None} for r in page])


class TemplateView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request):
        response = HttpResponse(TEMPLATE_CSV, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="plantilla-importar-ventas.csv"'
        return response
