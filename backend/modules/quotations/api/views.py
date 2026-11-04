from datetime import date

from django.db import transaction
from rest_framework import status as http
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.quotations.application.proformas import PriceEditNotAllowed, ProformaService
from modules.quotations.domain.proforma import (
    STATUSES, ProformaNotFound, ProformaStateError, ProformaValidationError,
)
from modules.quotations.infrastructure.adapters import CustomerLookup, ServiceLookup
from modules.quotations.infrastructure.django.repositories import DjangoProformaRepository, to_domain
from shared.tenancy import company_id_from

from .serializers import ProformaInputSerializer, detail_data, summary_data

REQUIRED_MODULES = ('quotations',)


class Conflict(APIException):
    status_code = http.HTTP_409_CONFLICT
    default_detail = 'La operación no es válida para el estado actual.'
    default_code = 'conflict'


def can_edit_price(user) -> bool:
    """Política de precios: hoy solo el administrador fija un precio distinto del catálogo.

    El módulo no importa `accounts`; lee el rol por nombre. Un rol futuro sin permiso recibe 403 sin cambiar la API.
    """
    return getattr(user, 'role', None) == 'admin'


class ProformaPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        for field in ('page', 'page_size'):
            raw = request.query_params.get(field)
            if raw is not None and (len(raw) > 10 or not raw.isascii() or not raw.isdigit() or int(raw) < 1):
                raise ValidationError({field: ['Ingresa un entero mayor que cero.']})
        try:
            return super().paginate_queryset(queryset, request, view=view)
        except NotFound as exc:
            raise ValidationError({'page': ['La página solicitada ya no está disponible.']}) from exc


def _service(request) -> ProformaService:
    company_id = company_id_from(request)
    return ProformaService(DjangoProformaRepository(company_id), ServiceLookup(company_id),
                           CustomerLookup(company_id), can_edit_price=can_edit_price(request.user),
                           user_id=request.user.pk)


def _detail(service: ProformaService, proforma) -> dict:
    return detail_data(proforma, allowed_actions=service.allowed_actions(proforma),
                       can_edit_price=service.can_edit_price, versions=service.versions(proforma))


def _run(callback):
    try:
        with transaction.atomic():
            return callback()
    except ProformaNotFound as exc:
        raise NotFound('Proforma no encontrada.') from exc
    except ProformaValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except ProformaStateError as exc:
        raise Conflict(str(exc)) from exc
    except PriceEditNotAllowed as exc:
        raise PermissionDenied('No tienes permiso para editar precios.') from exc


def _date_param(request, name):
    raw = request.query_params.get(name, '')
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError({name: ['Usa el formato AAAA-MM-DD.']}) from exc


class ProformaListCreateView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request):
        status = request.query_params.get('status', '')
        if status and status not in STATUSES:
            raise ValidationError({'status': ['Estado inválido.']})
        rows = DjangoProformaRepository(company_id_from(request)).search(
            customer=request.query_params.get('customer', '').strip(), status=status,
            date_from=_date_param(request, 'from'), date_to=_date_param(request, 'to'))
        paginator = ProformaPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response([summary_data(to_domain(row)) for row in page])

    def post(self, request):
        serializer = ProformaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _service(request)
        proforma = _run(lambda: service.create(serializer.to_input()))
        return Response(_detail(service, proforma), status=201)


class ProformaDetailView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request, proforma_id):
        service = _service(request)
        return Response(_detail(service, _run(lambda: service.get(proforma_id))))

    def put(self, request, proforma_id):
        serializer = ProformaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _service(request)
        proforma = _run(lambda: service.update(proforma_id, serializer.to_input()))
        return Response(_detail(service, proforma))


class ProformaActionView(APIView):
    required_modules = REQUIRED_MODULES
    action = ''

    def post(self, request, proforma_id):
        service = _service(request)
        method = {'present': service.present, 'new_version': service.new_version}[self.action]
        proforma = _run(lambda: method(proforma_id))
        return Response(_detail(service, proforma), status=201 if self.action == 'new_version' else 200)
