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
    UpdateExpense,
    VoidExpense,
)
from modules.expenses.application.queries import GetExpense, GetExpenseCategory, ListExpenseCategories, ListExpenses
from modules.expenses.domain.exceptions import (
    ExpenseCategoryNotFound,
    ExpenseNotFound,
    ExpenseRuleViolation,
    ExpenseValidationError,
)
from modules.expenses.infrastructure.adapters import SystemClock
from modules.expenses.infrastructure.django.repositories import (
    DjangoExpenseCategoryRepository,
    DjangoExpenseRepository,
)

from .filters import parse_expense_filters
from .pagination import CategoryPagination, ExpensePagination
from .serializers import (
    CategoryInputSerializer,
    CategorySerializer,
    ExpenseInputSerializer,
    ExpenseSerializer,
    ExpenseSummarySerializer,
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


def _expense_response(expense, http_status: int = status.HTTP_200_OK) -> Response:
    categories = DjangoExpenseCategoryRepository().get_many([expense.category_id])
    return Response(ExpenseSerializer(expense, context={'categories': categories}).data, status=http_status)


def _parse_active(raw: str | None) -> bool | None:
    if raw is None or raw == '':
        return None
    if raw in ('true', 'false'):
        return raw == 'true'
    raise ValidationError({'active': ['Valor inválido: use "true" o "false".']})


class ExpenseListCreateView(APIView):
    def get(self, request):
        filters = parse_expense_filters(request.query_params)
        repository = DjangoExpenseRepository()
        expenses = _run(ListExpenses(repository), mutates=False, filters=filters)
        paginator = ExpensePagination()
        page = paginator.paginate_queryset(expenses, request, view=self)
        paginator.total_amount = repository.total_active(filters)
        categories = DjangoExpenseCategoryRepository().get_many({e.category_id for e in page})
        data = ExpenseSummarySerializer(page, many=True, context={'categories': categories}).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        values = _validated(ExpenseInputSerializer, request.data)
        use_case = CreateExpense(DjangoExpenseRepository(), DjangoExpenseCategoryRepository())
        expense = _run(use_case, **values)
        return _expense_response(expense, status.HTTP_201_CREATED)


class ExpenseDetailView(APIView):
    # Sin DELETE: los gastos se anulan, no se borran (la ausencia del método da 405).

    def get(self, request, expense_id: str):
        expense = _run(GetExpense(DjangoExpenseRepository()), mutates=False,
                       expense_id=_uuid(expense_id, EXPENSE_NOT_FOUND))
        return _expense_response(expense)

    def patch(self, request, expense_id: str):
        values = _validated(ExpenseInputSerializer, request.data, partial=True)
        use_case = UpdateExpense(DjangoExpenseRepository(), DjangoExpenseCategoryRepository())
        expense = _run(use_case, expense_id=_uuid(expense_id, EXPENSE_NOT_FOUND), **values)
        return _expense_response(expense)


class ExpenseVoidView(APIView):
    def post(self, request, expense_id: str):
        use_case = VoidExpense(DjangoExpenseRepository(), SystemClock())
        expense = _run(use_case, expense_id=_uuid(expense_id, EXPENSE_NOT_FOUND))
        return _expense_response(expense)


class CategoryListCreateView(APIView):
    def get(self, request):
        active = _parse_active(request.query_params.get('active'))
        search = request.query_params.get('search', '').strip() or None
        categories = _run(ListExpenseCategories(DjangoExpenseCategoryRepository()), mutates=False,
                          active=active, search=search)
        paginator = CategoryPagination()
        page = paginator.paginate_queryset(categories, request, view=self)
        return paginator.get_paginated_response(CategorySerializer(page, many=True).data)

    def post(self, request):
        values = _validated(CategoryInputSerializer, request.data)
        category = _run(CreateExpenseCategory(DjangoExpenseCategoryRepository()), **values)
        return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    def get(self, request, category_id: str):
        category = _run(GetExpenseCategory(DjangoExpenseCategoryRepository()), mutates=False,
                        category_id=_uuid(category_id, CATEGORY_NOT_FOUND))
        return Response(CategorySerializer(category).data)

    def patch(self, request, category_id: str):
        values = _validated(CategoryInputSerializer, request.data, partial=True)
        category = _run(RenameExpenseCategory(DjangoExpenseCategoryRepository()),
                        category_id=_uuid(category_id, CATEGORY_NOT_FOUND), **values)
        return Response(CategorySerializer(category).data)


class CategoryActivateView(APIView):
    def post(self, request, category_id: str):
        category = _run(ActivateExpenseCategory(DjangoExpenseCategoryRepository()),
                        category_id=_uuid(category_id, CATEGORY_NOT_FOUND))
        return Response(CategorySerializer(category).data)


class CategoryDeactivateView(APIView):
    def post(self, request, category_id: str):
        category = _run(DeactivateExpenseCategory(DjangoExpenseCategoryRepository()),
                        category_id=_uuid(category_id, CATEGORY_NOT_FOUND))
        return Response(CategorySerializer(category).data)
