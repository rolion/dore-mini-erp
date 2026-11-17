"""API de la configuración de asientos automáticos por módulo (CONT-12).

Como las cuentas, no exige Contabilidad habilitada: se configura antes de habilitarla. Permiso por defecto de la API
(administrador de la empresa); la empresa sale del usuario autenticado.
"""
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.accounting import services
from modules.accounting.domain.account import AccountValidationError
from modules.accounting.domain.posting import PostingNotFound, get_role, modules_using
from shared.tenancy import company_id_from

from .posting_serializers import (
    PostingAccountInputSerializer,
    serialize_category_row,
    serialize_posting_config,
    serialize_role_row,
    validation_errors,
)


def _call(function, *args):
    try:
        return function(*args)
    except AccountValidationError as exc:
        raise ValidationError(validation_errors(exc)) from exc
    except PostingNotFound as exc:
        raise NotFound('No existe en la configuración de asientos automáticos.') from exc


class _PostingView(APIView):
    required_modules = ()


class PostingConfigView(_PostingView):
    def get(self, request):
        module = request.query_params.get('module') or ''
        return Response(serialize_posting_config(_call(services.describe_posting_config,
                                                       company_id_from(request), module)))


class PostingRoleView(_PostingView):
    def put(self, request, role):
        serializer = PostingAccountInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company_id = company_id_from(request)
        _call(get_role, role)
        _call(services.set_role_account, company_id, role, serializer.validated_data['account_id'])
        ref = services.describe_posting_config(company_id, modules_using(role)[0])
        return Response(serialize_role_row(next(r for r in ref.config.roles if r.role == role)))


class PostingCategoryView(_PostingView):
    """Cuenta de gasto de una categoría de Gastos. El id de la categoría es opaco para Contabilidad."""

    def put(self, request, category_id):
        serializer = PostingAccountInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company_id = company_id_from(request)
        _call(services.set_category_account, company_id, category_id, serializer.validated_data['account_id'])
        ref = services.describe_posting_config(company_id, 'expenses')
        row = next((c for c in ref.config.categories if c.category_id == category_id), None)
        return Response(serialize_category_row(row) if row else
                        {'category_id': str(category_id), 'account': None, 'issue': None})
