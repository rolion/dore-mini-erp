from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from django.utils import timezone

from modules.accounting.application.coverage import GetSettings, UpdateCutoff
from modules.accounting.application.regularization_summary import build_summary
from modules.accounting.application.regularize import RegularizationInProgress, RegularizeLedger
from modules.accounting.application.use_cases import (
    ActivateAccount,
    ConfigureMethod,
    ListAccountClasses,
    SetAccountClassEnabled,
    CreateAccount,
    CreateClassification,
    DeactivateAccount,
    GetAccount,
    GetClassification,
    GetEntry,
    ListAccounts,
    ListClassifications,
    ListEntries,
    ListMethods,
    RenameClassification,
    SetClassificationActive,
    UpdateAccount,
)
from modules.accounting.domain.account import (
    AccountConflict,
    AccountNotFound,
    AccountValidationError,
    MethodNotFound,
)
from modules.accounting.domain.account_class import AccountClassNotFound, parse_account_class
from modules.accounting.domain.catalog import DIRECTIONS
from modules.accounting.domain.classification import ClassificationNotFound
from modules.accounting.domain.entry import EntryNotFound
from modules.accounting.domain.regularization import HistoricalMapping, RegularizationInputError, parse_mapping
from modules.accounting.infrastructure.adapters import (
    DjangoRegularizationLedger,
    ReceivablesPaymentSource,
    SalesPaymentSource,
)
from modules.accounting.infrastructure.django.repositories import (
    DjangoAccountClassRepository,
    DjangoAccountRepository,
    DjangoClassificationRepository,
    DjangoCoverageRepository,
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
    ClassificationInputSerializer,
    ClassificationUpdateSerializer,
    RegularizationApplySerializer,
    RegularizationInputSerializer,
    SettingsUpdateSerializer,
    MethodInputSerializer,
    serialize_account,
    serialize_account_class,
    serialize_classification,
    serialize_coverage,
    serialize_entry,
    serialize_totals,
    serialize_method,
    serialize_settings,
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
    except AccountClassNotFound as exc:
        raise NotFound('Clasificación contable no encontrada.') from exc
    except ClassificationNotFound as exc:
        raise NotFound('Clasificación no encontrada.') from exc
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


def _parse_account_class(raw: str | None) -> str | None:
    if raw is None or raw == '':
        return None
    try:
        return parse_account_class(raw)
    except AccountClassNotFound:
        raise ValidationError({'account_class': ['Clasificación contable desconocida.']}) from None


# La configuración no exige Contabilidad habilitada: hay que poder configurar antes de habilitarla.
class _ConfigView(APIView):
    required_modules = ()


class AccountListCreateView(_ConfigView):
    def get(self, request):
        accounts, _ = _repositories(request)
        result = _run(ListAccounts(accounts), _parse_active(request.query_params.get('active')),
                      _parse_account_class(request.query_params.get('account_class')))
        return Response([serialize_account(a) for a in result])

    def post(self, request):
        serializer = AccountInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        accounts, _ = _repositories(request)
        account = _run(CreateAccount(accounts, DjangoAccountClassRepository(company_id_from(request))),
                       **serializer.validated_data)
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
        classes = DjangoAccountClassRepository(company_id_from(request))
        account = _run(UpdateAccount(accounts, mappings, entries, classes), account_id, **serializer.validated_data)
        return Response(serialize_account(account))


class AccountActivateView(_ConfigView):
    def post(self, request, account_id):
        accounts, _ = _repositories(request)
        return Response(serialize_account(_run(ActivateAccount(accounts), account_id)))


class AccountDeactivateView(_ConfigView):
    def post(self, request, account_id):
        accounts, mappings = _repositories(request)
        return Response(serialize_account(_run(DeactivateAccount(accounts, mappings), account_id)))


def _coverage_use_case(request, use_case_class):
    """Caso de uso de corte/cobertura de la empresa del usuario (si Contabilidad está habilitada o no)."""
    company_id = company_id_from(request)
    return use_case_class(DjangoCoverageRepository(company_id), DjangoEntryRepository(company_id),
                          timezone.localdate(), module_gate.is_enabled(company_id, 'accounting'))


class AccountClassListView(_ConfigView):
    def get(self, request):
        repository = DjangoAccountClassRepository(company_id_from(request))
        return Response([serialize_account_class(v) for v in _run(ListAccountClasses(repository))])


class _AccountClassToggleView(_ConfigView):
    enabled = True

    def post(self, request, code):
        repository = DjangoAccountClassRepository(company_id_from(request))
        return Response(serialize_account_class(_run(SetAccountClassEnabled(repository, self.enabled), code)))


class AccountClassEnableView(_AccountClassToggleView):
    enabled = True


class AccountClassDisableView(_AccountClassToggleView):
    enabled = False


class SettingsView(_ConfigView):
    """Corte y cobertura de Contabilidad: se consulta aunque el módulo esté deshabilitado."""

    def get(self, request):
        return Response(serialize_settings(_run(_coverage_use_case(request, GetSettings))))

    def patch(self, request):
        serializer = SettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        use_case = _coverage_use_case(request, UpdateCutoff)
        return Response(serialize_settings(_run(use_case, serializer.validated_data['cutoff_date'])))


class ClassificationListCreateView(_ConfigView):
    def get(self, request):
        direction = request.query_params.get('direction') or None
        if direction is not None and direction not in DIRECTIONS:
            raise ValidationError({'direction': [f'Valor inválido; use uno de: {", ".join(DIRECTIONS)}.']})
        repository = DjangoClassificationRepository(company_id_from(request))
        result = _run(ListClassifications(repository), _parse_active(request.query_params.get('active')), direction)
        return Response([serialize_classification(c) for c in result])

    def post(self, request):
        serializer = ClassificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repository = DjangoClassificationRepository(company_id_from(request))
        created = _run(CreateClassification(repository), **serializer.validated_data)
        return Response(serialize_classification(created), status=status.HTTP_201_CREATED)


class ClassificationDetailView(_ConfigView):
    def get(self, request, classification_id):
        repository = DjangoClassificationRepository(company_id_from(request))
        return Response(serialize_classification(_run(GetClassification(repository), classification_id)))

    def patch(self, request, classification_id):
        serializer = ClassificationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repository = DjangoClassificationRepository(company_id_from(request))
        updated = _run(RenameClassification(repository), classification_id, serializer.validated_data['name'])
        return Response(serialize_classification(updated))


class ClassificationActivateView(_ConfigView):
    def post(self, request, classification_id):
        repository = DjangoClassificationRepository(company_id_from(request))
        return Response(serialize_classification(
            _run(SetClassificationActive(repository, True), classification_id)))


class ClassificationDeactivateView(_ConfigView):
    def post(self, request, classification_id):
        repository = DjangoClassificationRepository(company_id_from(request))
        return Response(serialize_classification(
            _run(SetClassificationActive(repository, False), classification_id)))


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


def _classification_names(company_id) -> dict:
    return {c.id: c.name for c in DjangoClassificationRepository(company_id).list()}


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
        names = _classification_names(company_id)
        response = paginator.get_paginated_response([serialize_entry(row, enabled, names) for row in page])
        response.data['totals'] = serialize_totals(totals)
        response.data['period'] = {'date_from': filters.date_from, 'date_to': filters.date_to}
        settings_view = GetSettings(DjangoCoverageRepository(company_id), DjangoEntryRepository(company_id),
                                    timezone.localdate(), True).execute()
        response.data['coverage'] = serialize_coverage(coverage, settings_view)
        return response


class EntryDetailView(APIView):
    required_modules = ('accounting',)

    def get(self, request, entry_id):
        company_id = company_id_from(request)
        row = _run(GetEntry(DjangoEntryRepository(company_id)), entry_id)
        return Response(serialize_entry(row, module_gate.enabled_keys(company_id), _classification_names(company_id),
                                        detail=True))


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
        if not data['mapping']:
            # Sin reglas todo queda pendiente: se puede previsualizar, pero no hay nada que aplicar.
            if self.applies:
                raise ValidationError({'mapping': ['Agrega al menos una regla de mapeo para aplicar.']})
            mapping = HistoricalMapping({})
        else:
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
        return Response(build_summary(report, accounts, self.applies, data['date_from'], data['date_to'], mapping))


class RegularizationPreviewView(_RegularizationView):
    """Previsualización: lee y compara; no escribe nada."""


class RegularizationApplyView(_RegularizationView):
    serializer_class = RegularizationApplySerializer
    applies = True
