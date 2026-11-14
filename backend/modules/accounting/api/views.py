from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from django.utils import timezone

from modules.accounting.application.regularization_summary import build_summary
from modules.accounting.application.regularize import RegularizationInProgress, RegularizeLedger
from modules.accounting.application.use_cases import (
    ActivateAccount,
    ConfigureMethod,
    CreateAccount,
    DeactivateAccount,
    GetAccount,
    GetEntry,
    ListAccounts,
    ListEntries,
    ListMethods,
    UpdateAccount,
)
from modules.accounting.domain.account import (
    AccountConflict,
    AccountNotFound,
    AccountValidationError,
    MethodNotFound,
)
from modules.accounting.domain.entry import EntryNotFound
from modules.accounting.domain.regularization import RegularizationInputError, parse_mapping
from modules.accounting.infrastructure.adapters import (
    DjangoRegularizationLedger,
    ReceivablesPaymentSource,
    SalesPaymentSource,
)
from modules.accounting.infrastructure.django.repositories import (
    DjangoAccountRepository,
    DjangoEntryRepository,
    DjangoMethodMappingRepository,
    EntryFilters,
)
from shared import module_gate
from shared.tenancy import company_id_from

from .serializers import (
    AccountInputSerializer,
    EntryFiltersSerializer,
    AccountUpdateSerializer,
    RegularizationApplySerializer,
    RegularizationInputSerializer,
    MethodInputSerializer,
    serialize_account,
    serialize_coverage,
    serialize_entry,
    serialize_totals,
    serialize_method,
)


class Conflict(APIException):
    """409 con `{detail, code, methods}`."""

    status_code = status.HTTP_409_CONFLICT

    def __init__(self, detail: str, code: str, methods: list[str]):
        super().__init__({'detail': detail, 'code': code, 'methods': methods})


def _repositories(request):
    """Repositorios de la empresa del usuario autenticado (nunca de un dato enviado por el cliente)."""
    company_id = company_id_from(request)
    return DjangoAccountRepository(company_id), DjangoMethodMappingRepository(company_id)


def _run(use_case, *args, **kwargs):
    try:
        with transaction.atomic():
            return use_case.execute(*args, **kwargs)
    except AccountValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except AccountNotFound as exc:
        raise NotFound('Cuenta no encontrada.') from exc
    except MethodNotFound as exc:
        raise NotFound('Método de pago no encontrado.') from exc
    except EntryNotFound as exc:
        raise NotFound('Entrada no encontrada.') from exc
    except AccountConflict as exc:
        raise Conflict(str(exc), exc.code, exc.methods) from exc


def _parse_active(raw: str | None) -> bool | None:
    if raw is None or raw == '':
        return None
    if raw in ('true', 'false'):
        return raw == 'true'
    raise ValidationError({'active': ['Valor inválido: use "true" o "false".']})


# La configuración no exige Contabilidad habilitada: hay que poder configurar antes de habilitarla.
class _ConfigView(APIView):
    required_modules = ()


class AccountListCreateView(_ConfigView):
    def get(self, request):
        accounts, _ = _repositories(request)
        result = _run(ListAccounts(accounts), _parse_active(request.query_params.get('active')))
        return Response([serialize_account(a) for a in result])

    def post(self, request):
        serializer = AccountInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        accounts, _ = _repositories(request)
        account = _run(CreateAccount(accounts), **serializer.validated_data)
        return Response(serialize_account(account), status=status.HTTP_201_CREATED)


class AccountDetailView(_ConfigView):
    def get(self, request, account_id):
        accounts, _ = _repositories(request)
        return Response(serialize_account(_run(GetAccount(accounts), account_id)))

    def patch(self, request, account_id):
        serializer = AccountUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        accounts, mappings = _repositories(request)
        entries = DjangoEntryRepository(company_id_from(request))
        account = _run(UpdateAccount(accounts, mappings, entries), account_id, **serializer.validated_data)
        return Response(serialize_account(account))


class AccountActivateView(_ConfigView):
    def post(self, request, account_id):
        accounts, _ = _repositories(request)
        return Response(serialize_account(_run(ActivateAccount(accounts), account_id)))


class AccountDeactivateView(_ConfigView):
    def post(self, request, account_id):
        accounts, mappings = _repositories(request)
        return Response(serialize_account(_run(DeactivateAccount(accounts, mappings), account_id)))


class MethodListView(_ConfigView):
    def get(self, request):
        accounts, mappings = _repositories(request)
        return Response([serialize_method(v) for v in _run(ListMethods(accounts, mappings))])


class MethodDetailView(_ConfigView):
    def put(self, request, code):
        serializer = MethodInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        accounts, mappings = _repositories(request)
        view = _run(ConfigureMethod(accounts, mappings), code.upper(), serializer.validated_data['account_id'],
                    serializer.validated_data['is_active'])
        return Response(serialize_method(view))


class EntryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class EntryListView(APIView):
    """Libro de entradas: solo lectura. No hay rutas de alta, edición ni borrado."""

    required_modules = ('accounting',)

    def get(self, request):
        company_id = company_id_from(request)
        serializer = EntryFiltersSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = EntryFilters(**serializer.validated_data)
        if filters.account_id and DjangoAccountRepository(company_id).get(filters.account_id) is None:
            raise ValidationError({'account_id': ['La cuenta no existe en esta empresa.']})
        rows, totals, coverage = ListEntries(DjangoEntryRepository(company_id)).execute(filters)
        paginator = EntryPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        enabled = module_gate.enabled_keys(company_id)
        response = paginator.get_paginated_response([serialize_entry(row, enabled) for row in page])
        response.data['totals'] = serialize_totals(totals)
        response.data['period'] = {'date_from': filters.date_from, 'date_to': filters.date_to}
        response.data['coverage'] = serialize_coverage(coverage)
        return response


class EntryDetailView(APIView):
    required_modules = ('accounting',)

    def get(self, request, entry_id):
        company_id = company_id_from(request)
        row = _run(GetEntry(DjangoEntryRepository(company_id)), entry_id)
        return Response(serialize_entry(row, module_gate.enabled_keys(company_id), detail=True))


class _RegularizationView(APIView):
    """Regularización de pagos históricos (PB-ACC-004): solo admin de la empresa de la sesión, con Contabilidad."""

    required_modules = ('accounting',)
    serializer_class = RegularizationInputSerializer
    applies = False

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        company_id = company_id_from(request)
        accounts = DjangoAccountRepository(company_id).by_id()
        try:
            mapping = parse_mapping(data['mapping'], accounts)
        except RegularizationInputError as exc:
            raise ValidationError({'mapping': exc.errors}) from exc
        use_case = RegularizeLedger(
            {'PRODUCT': SalesPaymentSource(), 'SERVICE': ReceivablesPaymentSource()}, DjangoRegularizationLedger())
        if self.applies:
            user = request.user
            executed_by = user.get_full_name().strip() or user.get_username()
            try:
                report = use_case.apply(company_id, data['date_from'], data['date_to'], mapping, executed_by,
                                        timezone.now())
            except RegularizationInProgress as exc:
                raise Conflict(str(exc), 'regularization_in_progress', []) from exc
        else:
            report = use_case.plan(company_id, data['date_from'], data['date_to'], mapping)
        return Response(build_summary(report, accounts, self.applies))


class RegularizationPreviewView(_RegularizationView):
    """Previsualización: lee y compara; no escribe nada."""


class RegularizationApplyView(_RegularizationView):
    serializer_class = RegularizationApplySerializer
    applies = True
