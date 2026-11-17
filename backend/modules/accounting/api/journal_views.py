"""API del libro de asientos (CONT-11): lista, alta manual, detalle y reversión. Sin edición ni borrado."""
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.accounting import services
from modules.accounting.domain.fiscal_period import DateOutsideFiscalPeriod, FiscalPeriodClosed
from modules.accounting.domain.journal import JournalConflict, JournalEntryNotFound, JournalValidationError
from modules.accounting.infrastructure.django.repositories import (
    DjangoAccountRepository,
    DjangoFiscalPeriodRepository,
    DjangoJournalRepository,
    JournalFilters,
)
from shared import module_gate
from shared.tenancy import company_id_from

from .journal_serializers import (
    JournalEntryInputSerializer,
    JournalFiltersSerializer,
    JournalReverseSerializer,
    serialize_journal_detail,
    serialize_journal_row,
)


class JournalPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class JournalConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT


def _author(request) -> tuple[int, str]:
    user = request.user
    return user.pk, user.get_full_name().strip() or user.get_username()


def _detail(company_id, entry_id) -> dict:
    journal = DjangoJournalRepository(company_id)
    entry = journal.get(entry_id)
    if entry is None:
        raise NotFound('Asiento no encontrado.')
    period = DjangoFiscalPeriodRepository(company_id).get(entry.period_id) if entry.period_id else None
    accounts = DjangoAccountRepository(company_id).by_id()
    return serialize_journal_detail(entry, accounts, period, module_gate.enabled_keys(company_id))


def _fail(exc: Exception, date_field: str):
    if isinstance(exc, JournalValidationError):
        raise ValidationError(exc.errors) from exc
    if isinstance(exc, (DateOutsideFiscalPeriod, FiscalPeriodClosed)):
        raise ValidationError({date_field: [str(exc)]}) from exc
    if isinstance(exc, JournalEntryNotFound):
        raise NotFound('Asiento no encontrado.') from exc
    if isinstance(exc, JournalConflict):
        raise JournalConflictError({'detail': str(exc), 'code': exc.code}) from exc
    raise exc


class JournalEntryListCreateView(APIView):
    required_modules = ('accounting',)

    def get(self, request):
        company_id = company_id_from(request)
        serializer = JournalFiltersSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = JournalFilters(**serializer.validated_data)
        if filters.account_id and DjangoAccountRepository(company_id).get(filters.account_id) is None:
            raise ValidationError({'account_id': ['La cuenta no existe en esta empresa.']})
        paginator = JournalPagination()
        page = paginator.paginate_queryset(DjangoJournalRepository(company_id).search(filters), request, view=self)
        enabled = module_gate.enabled_keys(company_id)
        return paginator.get_paginated_response([serialize_journal_row(row, enabled) for row in page])

    def post(self, request):
        company_id = company_id_from(request)
        serializer = JournalEntryInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user_id, user_name = _author(request)
        lines = [services.JournalLineInput(line['account_id'], debit=line.get('debit'), credit=line.get('credit'),
                                           memo=line.get('memo', '')) for line in data['lines']]
        try:
            with transaction.atomic():
                posted = services.post_journal_entry(company_id, services.JournalEntryInput(
                    accounting_date=data['accounting_date'], description=data['description'], lines=lines,
                    created_by=user_id, created_by_name=user_name))
        except Exception as exc:  # noqa: BLE001 — se traducen los errores de dominio; el resto se relanza
            _fail(exc, 'accounting_date')
        return Response(_detail(company_id, posted.entry.id), status=status.HTTP_201_CREATED)


class JournalEntryDetailView(APIView):
    required_modules = ('accounting',)

    def get(self, request, entry_id):
        return Response(_detail(company_id_from(request), entry_id))


class JournalEntryReverseView(APIView):
    required_modules = ('accounting',)

    def post(self, request, entry_id):
        company_id = company_id_from(request)
        serializer = JournalReverseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user_id, user_name = _author(request)
        try:
            with transaction.atomic():
                posted = services.reverse_journal_entry(company_id, entry_id, data['reversal_date'], data['reason'],
                                                        user_id, user_name)
        except Exception as exc:  # noqa: BLE001
            _fail(exc, 'reversal_date')
        return Response(_detail(company_id, posted.entry.id),
                        status=status.HTTP_201_CREATED if posted.created else status.HTTP_200_OK)
