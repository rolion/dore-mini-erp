from uuid import UUID

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.expenses.application.commands import (
    ActivateExpenseCategory,
    CreateExpense,
    CreateExpenseCategory,
    DeactivateExpenseCategory,
    RenameExpenseCategory,
    SetCategoryClassification,
    UpdateExpense,
    VoidExpense,
)
from modules.expenses.application.queries import GetExpense, GetExpenseCategory, ListExpenseCategories, ListExpenses
from modules.expenses.domain.exceptions import (
    ExpenseCategoryNotFound,
    ExpenseNotFound,
    ExpensePostingError,
    ExpenseRuleViolation,
    ExpenseValidationError,
)
from modules.expenses.infrastructure.adapters import (
    AccountingAccounts,
    AccountingClassifications,
    AccountingPosting,
    SystemClock,
)
from modules.expenses.infrastructure.django.repositories import (
    DjangoExpenseCategoryRepository,
    DjangoExpenseRepository,
)
from shared.tenancy import company_id_from

from .filters import parse_expense_filters
from .pagination import CategoryPagination, ExpensePagination
from .serializers import (
    CategoryClassificationInputSerializer,
    CategoryInputSerializer,
    CategorySerializer,
    ExpenseCreateSerializer,
    ExpenseInputSerializer,
    ExpenseSerializer,
    ExpenseSummarySerializer,
    PostingOptionsQuerySerializer,
    account_data,
)

EXPENSE_NOT_FOUND = 'Gasto no encontrado.'
CATEGORY_NOT_FOUND = 'Categoría no encontrada.'


class RuleConflict(APIException):
    """409 con `{code, detail}`: el recurso existe pero su estado no admite la acción."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Conflicto con el estado actual del recurso.'


def _uuid(raw: str, message: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError:
        raise NotFound(message) from None


def _run(use_case, mutates: bool = True, **kwargs):
    """Ejecuta un caso de uso traduciendo errores de dominio a HTTP.

    Las mutaciones corren en una transacción: el repositorio bloquea la fila con `select_for_update`, que exige
    transacción abierta, y así se serializan escrituras concurrentes (p. ej. dos anulaciones del mismo gasto).
    """
    try:
        if mutates:
            with transaction.atomic():
                return use_case.execute(**kwargs)
        return use_case.execute(**kwargs)
    except ExpensePostingError as exc:
        if exc.code == 'posting_configuration_missing':
            raise ValidationError({'code': exc.code, 'detail': exc.message, 'issues': exc.issues}) from exc
        raise RuleConflict({'code': exc.code, 'detail': exc.message}) from exc
    except ExpenseValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except ExpenseRuleViolation as exc:
        raise RuleConflict({'code': exc.code, 'detail': exc.message}) from exc
    except ExpenseNotFound as exc:
        raise NotFound(EXPENSE_NOT_FOUND) from exc
    except ExpenseCategoryNotFound as exc:
        raise NotFound(CATEGORY_NOT_FOUND) from exc


def _validated(serializer_class, data, partial: bool = False) -> dict:
    serializer = serializer_class(data=data, partial=partial)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def _expenses(request) -> DjangoExpenseRepository:
    """Repositorios de la empresa del usuario autenticado (nunca de un dato enviado por el cliente)."""
    return DjangoExpenseRepository(company_id_from(request))


def _categories(request) -> DjangoExpenseCategoryRepository:
    return DjangoExpenseCategoryRepository(company_id_from(request))


def _classifications(request) -> AccountingClassifications:
    return AccountingClassifications(company_id_from(request))


def _posting(request) -> AccountingPosting:
    return AccountingPosting(company_id_from(request))


def _context(request, expenses, categories) -> dict:
    """Contexto de los serializers: categorías, clasificaciones y cuentas de la página, en una consulta por lote."""
    ids = {e.classification_id for e in expenses if e.classification_id is not None}
    account_ids = {a for e in expenses for a in (e.expense_account_id, e.payment_account_id) if a is not None}
    return {'categories': categories, 'classifications': _classifications(request).describe(ids),
            'accounts': AccountingAccounts(company_id_from(request)).describe(account_ids)}


def _expense_response(request, expense, http_status: int = status.HTTP_200_OK, replayed: bool = False) -> Response:
    categories = _categories(request).get_many([expense.category_id])
    context = _context(request, [expense], categories)
    if expense.is_posted:
        context['journal_entry_id'] = _posting(request).entry_id(expense.id)
    data = {**ExpenseSerializer(expense, context=context).data, 'replayed': replayed}
    return Response(data, status=http_status)


def _category_response(request, category, http_status: int = status.HTTP_200_OK) -> Response:
    ids = [category.classification_id] if category.classification_id else []
    context = {'classifications': _classifications(request).describe(ids)}
    return Response(CategorySerializer(category, context=context).data, status=http_status)


def _parse_active(raw: str | None) -> bool | None:
    if raw is None or raw == '':
        return None
    if raw in ('true', 'false'):
        return raw == 'true'
    raise ValidationError({'active': ['Valor inválido: use "true" o "false".']})


class ExpenseListCreateView(APIView):
    required_modules = ('expenses',)
    def get(self, request):
        filters = parse_expense_filters(request.query_params)
        repository = _expenses(request)
        expenses = _run(ListExpenses(repository), mutates=False, filters=filters)
        paginator = ExpensePagination()
        page = paginator.paginate_queryset(expenses, request, view=self)
        paginator.total_amount = repository.total_active(filters)
        categories = _categories(request).get_many({e.category_id for e in page})
        data = ExpenseSummarySerializer(page, many=True, context=_context(request, page, categories)).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        values = _validated(ExpenseCreateSerializer, request.data)
        use_case = CreateExpense(_expenses(request), _categories(request), _classifications(request),
                                 _posting(request))
        expense = _run(use_case, **values)
        return _expense_response(request, expense, status.HTTP_200_OK if use_case.replayed else status.HTTP_201_CREATED,
                                 replayed=use_case.replayed)


class ExpensePostingOptionsView(APIView):
    """Cuentas por defecto y elegibles para contabilizar un gasto (solo lectura): alimenta el formulario."""

    required_modules = ('expenses',)

    def get(self, request):
        params = _validated(PostingOptionsQuerySerializer, request.query_params)
        category = _categories(request).get(params['category_id']) if params.get('category_id') else None
        method = (params.get('payment_method') or '').strip().upper() or None
        options = AccountingAccounts(company_id_from(request)).options(
            params['expense_date'], method, category.id if category else None, category.name if category else '')
        defaults = options.defaults
        return Response({
            'covered': options.covered,
            'reason': options.reason,
            'expense_account': account_data(defaults['EXPENSE_BY_CATEGORY']) if 'EXPENSE_BY_CATEGORY' in defaults else None,
            'payment_account': account_data(defaults['MONEY']) if 'MONEY' in defaults else None,
            'issues': [{'code': i.code, 'role': i.role, 'subject': i.subject, 'message': i.message}
                       for i in options.issues],
            'expense_accounts': [account_data(a) for a in options.eligible.get('EXPENSE_BY_CATEGORY', ())],
            'payment_accounts': [account_data(a) for a in options.eligible.get('MONEY', ())],
        })


class ExpenseDetailView(APIView):
    required_modules = ('expenses',)
    # Sin DELETE: los gastos se anulan, no se borran (la ausencia del método da 405).

    def get(self, request, expense_id: str):
        expense = _run(GetExpense(_expenses(request)), mutates=False,
                       expense_id=_uuid(expense_id, EXPENSE_NOT_FOUND))
        return _expense_response(request, expense)

    def patch(self, request, expense_id: str):
        values = _validated(ExpenseInputSerializer, request.data, partial=True)
        use_case = UpdateExpense(_expenses(request), _categories(request), _classifications(request))
        expense = _run(use_case, expense_id=_uuid(expense_id, EXPENSE_NOT_FOUND), **values)
        return _expense_response(request, expense)


class ExpenseVoidView(APIView):
    required_modules = ('expenses',)
    def post(self, request, expense_id: str):
        use_case = VoidExpense(_expenses(request), SystemClock(), _posting(request))
        expense = _run(use_case, expense_id=_uuid(expense_id, EXPENSE_NOT_FOUND))
        return _expense_response(request, expense)


class CategoryListCreateView(APIView):
    required_modules = ('expenses',)
    def get(self, request):
        active = _parse_active(request.query_params.get('active'))
        search = request.query_params.get('search', '').strip() or None
        categories = _run(ListExpenseCategories(_categories(request)), mutates=False,
                          active=active, search=search)
        paginator = CategoryPagination()
        page = paginator.paginate_queryset(categories, request, view=self)
        ids = {c.classification_id for c in page if c.classification_id is not None}
        context = {'classifications': _classifications(request).describe(ids)}
        return paginator.get_paginated_response(CategorySerializer(page, many=True, context=context).data)

    def post(self, request):
        values = _validated(CategoryInputSerializer, request.data)
        category = _run(CreateExpenseCategory(_categories(request)), **values)
        return _category_response(request, category, status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    required_modules = ('expenses',)
    def get(self, request, category_id: str):
        category = _run(GetExpenseCategory(_categories(request)), mutates=False,
                        category_id=_uuid(category_id, CATEGORY_NOT_FOUND))
        return _category_response(request, category)

    def patch(self, request, category_id: str):
        values = _validated(CategoryInputSerializer, request.data, partial=True)
        category = _run(RenameExpenseCategory(_categories(request)),
                        category_id=_uuid(category_id, CATEGORY_NOT_FOUND), **values)
        return _category_response(request, category)


class CategoryActivateView(APIView):
    required_modules = ('expenses',)
    def post(self, request, category_id: str):
        category = _run(ActivateExpenseCategory(_categories(request)),
                        category_id=_uuid(category_id, CATEGORY_NOT_FOUND))
        return _category_response(request, category)


class CategoryDeactivateView(APIView):
    required_modules = ('expenses',)
    def post(self, request, category_id: str):
        category = _run(DeactivateExpenseCategory(_categories(request)),
                        category_id=_uuid(category_id, CATEGORY_NOT_FOUND))
        return _category_response(request, category)


class CategoryClassificationView(APIView):
    """Asocia (o quita) la clasificación de egreso de una categoría; no reclasifica gastos ya registrados."""

    required_modules = ('expenses',)

    def put(self, request, category_id: str):
        values = _validated(CategoryClassificationInputSerializer, request.data)
        use_case = SetCategoryClassification(_categories(request), _classifications(request))
        category = _run(use_case, category_id=_uuid(category_id, CATEGORY_NOT_FOUND),
                        classification_id=values['classification_id'])
        return _category_response(request, category)
