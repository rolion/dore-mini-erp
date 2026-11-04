from datetime import date, datetime, timezone
from uuid import UUID

from django.db import transaction
from rest_framework import status as http
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import CompanyClinicalPermission, CompanyModulePermission
from modules.receivables.application.collections import CollectionService
from modules.receivables.domain.obligation import (
    KINDS, PAID, PARTIAL, PENDING, CommitmentNotFound, ObligationStateError, ObligationValidationError,
)
from modules.receivables.infrastructure.adapters import source_for
from modules.receivables.infrastructure.django.repositories import DjangoObligationRepository
from shared.tenancy import company_id_from

from .serializers import PaymentInputSerializer, detail_data, payment_data, summary_data

# Módulos de cada fuente, igual que en sus propias APIs.
SOURCE_MODULES = {'quotation': ('quotations',), 'dental': ('dentistry', 'customers', 'services')}
STATUSES = (PENDING, PARTIAL, PAID)


class Conflict(APIException):
    status_code = http.HTTP_409_CONFLICT
    default_detail = 'La operación no es válida para el estado actual.'
    default_code = 'conflict'


class _Gate:
    """Vista mínima para reutilizar los permisos de la API con los módulos de la fuente concreta."""

    def __init__(self, required_modules):
        self.required_modules = required_modules


def _authorize(request, kind: str) -> None:
    if kind not in KINDS:
        raise NotFound('Compromiso no encontrado.')
    permission = CompanyClinicalPermission if kind == 'dental' else CompanyModulePermission
    if not permission().has_permission(request, _Gate(('receivables',) + SOURCE_MODULES[kind])):
        raise PermissionDenied()


def _user_name(user) -> str:
    full = user.get_full_name() if hasattr(user, 'get_full_name') else ''
    return (full or user.get_username())[:150]


def _service(request) -> CollectionService:
    company_id = company_id_from(request)
    return CollectionService(
        DjangoObligationRepository(company_id), lambda kind: source_for(kind, company_id),
        today=lambda: datetime.now(timezone.utc).date(), now=lambda: datetime.now(timezone.utc),
        user_id=request.user.pk, user_name=_user_name(request.user))


def _run(callback):
    try:
        with transaction.atomic():
            return callback()
    except CommitmentNotFound as exc:
        raise NotFound('Compromiso no encontrado.') from exc
    except ObligationValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except ObligationStateError as exc:
        raise Conflict(str(exc)) from exc


def _date_param(request, name):
    raw = request.query_params.get(name, '')
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError({name: ['Usa el formato AAAA-MM-DD.']}) from exc


class ObligationPagination(PageNumberPagination):
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


class ObligationListView(APIView):
    required_modules = ('receivables',)

    def get(self, request):
        status = request.query_params.get('status', '')
        if status and status not in STATUSES:
            raise ValidationError({'status': ['Estado inválido.']})
        customer_raw = request.query_params.get('customer_id', '')
        try:
            customer_id = UUID(customer_raw) if customer_raw else None
        except ValueError as exc:
            raise ValidationError({'customer_id': ['Identificador inválido.']}) from exc
        views = _service(request).list(customer_id=customer_id, date_from=_date_param(request, 'date_from'),
                                       date_to=_date_param(request, 'date_to'), status=status)
        # Cada fuente solo se ofrece si su módulo está habilitado (y, en Odontología, con acceso clínico).
        visible = []
        for view in views:
            try:
                _authorize(request, view.snapshot.kind)
            except Exception:  # noqa: BLE001 - módulo deshabilitado o sin acceso: no se lista
                continue
            visible.append(view)
        paginator = ObligationPagination()
        page = paginator.paginate_queryset(visible, request, view=self)
        return paginator.get_paginated_response([summary_data(v) for v in page])


class CommitmentDetailView(APIView):
    required_modules = ('receivables',)

    def get(self, request, kind, number):
        _authorize(request, kind)
        return Response(detail_data(_run(lambda: _service(request).get(kind, number))))


class PaymentCreateView(APIView):
    """Registra un anticipo o abono (idempotente por `idempotency_key`)."""
    required_modules = ('receivables',)

    def post(self, request, kind, number):
        _authorize(request, kind)
        serializer = PaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _service(request)
        result = _run(lambda: service.register_payment(kind, number, serializer.to_input()))
        return Response({**detail_data(result.view), 'payment': payment_data(result.payment),
                         'replayed': result.replayed}, status=200 if result.replayed else 201)
