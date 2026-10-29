from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.purchases.application.commands import (
    ActivateSupplier,
    CreateSupplier,
    DeactivateSupplier,
    UpdateSupplier,
)
from modules.purchases.application.queries import GetSupplier, ListSuppliers
from modules.purchases.domain.exceptions import SupplierNotFound, SupplierValidationError
from modules.purchases.infrastructure.django.repositories import DjangoSupplierRepository
from shared.tenancy import company_id_from

from .pagination import SupplierPagination
from .serializers import SupplierInputSerializer, SupplierSerializer

SUPPLIER_NOT_FOUND = 'Proveedor no encontrado.'
REQUIRED_MODULES = ('purchases',)


def _repository(request) -> DjangoSupplierRepository:
    """Repositorio de la empresa del usuario autenticado (nunca de un dato enviado por el cliente)."""
    return DjangoSupplierRepository(company_id_from(request))


def _run(use_case, **kwargs):
    """Ejecuta un caso de uso traduciendo errores de dominio a respuestas HTTP."""
    try:
        return use_case.execute(**kwargs)
    except SupplierValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except SupplierNotFound as exc:
        raise NotFound(SUPPLIER_NOT_FOUND) from exc


def _parse_active(raw: str | None) -> bool | None:
    if raw is None or raw == '':
        return None
    if raw in ('true', 'false'):
        return raw == 'true'
    raise ValidationError({'active': ['Valor inválido: use "true" o "false".']})


class SupplierListCreateView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request):
        active = _parse_active(request.query_params.get('active'))
        search = request.query_params.get('search', '').strip() or None
        suppliers = ListSuppliers(_repository(request)).execute(search=search, active=active)
        paginator = SupplierPagination()
        page = paginator.paginate_queryset(suppliers, request, view=self)
        return paginator.get_paginated_response(SupplierSerializer(page, many=True).data)

    def post(self, request):
        serializer = SupplierInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        supplier = _run(CreateSupplier(_repository(request)), **{'name': None, **serializer.validated_data})
        return Response(SupplierSerializer(supplier).data, status=status.HTTP_201_CREATED)


class SupplierDetailView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request, supplier_id):
        supplier = _run(GetSupplier(_repository(request)), supplier_id=supplier_id)
        return Response(SupplierSerializer(supplier).data)

    def patch(self, request, supplier_id):
        serializer = SupplierInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        supplier = _run(UpdateSupplier(_repository(request)), supplier_id=supplier_id, **serializer.validated_data)
        return Response(SupplierSerializer(supplier).data)


class SupplierActivateView(APIView):
    required_modules = REQUIRED_MODULES

    def post(self, request, supplier_id):
        supplier = _run(ActivateSupplier(_repository(request)), supplier_id=supplier_id)
        return Response(SupplierSerializer(supplier).data)


class SupplierDeactivateView(APIView):
    required_modules = REQUIRED_MODULES

    def post(self, request, supplier_id):
        supplier = _run(DeactivateSupplier(_repository(request)), supplier_id=supplier_id)
        return Response(SupplierSerializer(supplier).data)
