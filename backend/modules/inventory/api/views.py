from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.inventory.application.use_cases import (
    ActivateWarehouse,
    CreateWarehouse,
    DeactivateWarehouse,
    GetWarehouse,
    ListWarehouses,
    MakeDefaultWarehouse,
    UpdateWarehouse,
)
from modules.inventory.domain.exceptions import WarehouseConflict, WarehouseNotFound, WarehouseValidationError
from modules.inventory.infrastructure.activity import LedgerWarehouseActivity
from modules.inventory.infrastructure.django.repositories import DjangoWarehouseRepository
from shared.tenancy import company_id_from

from .pagination import WarehousePagination
from .serializers import WarehouseInputSerializer, WarehouseSerializer

WAREHOUSE_NOT_FOUND = 'Almacén no encontrado.'


class Conflict(APIException):
    """409 con `{detail, code}`."""

    status_code = status.HTTP_409_CONFLICT

    def __init__(self, detail: str, code: str):
        super().__init__({'detail': detail, 'code': code})


def _repository(request) -> DjangoWarehouseRepository:
    """Repositorio de la empresa del usuario autenticado (nunca de un dato enviado por el cliente)."""
    return DjangoWarehouseRepository(company_id_from(request))


def _run(use_case, **kwargs):
    try:
        return use_case.execute(**kwargs)
    except WarehouseValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except WarehouseNotFound as exc:
        raise NotFound(WAREHOUSE_NOT_FOUND) from exc
    except WarehouseConflict as exc:
        raise Conflict(str(exc), exc.code) from exc


def _parse_active(raw: str | None) -> bool | None:
    if raw is None or raw == '':
        return None
    if raw in ('true', 'false'):
        return raw == 'true'
    raise ValidationError({'active': ['Valor inválido: use "true" o "false".']})


class WarehouseListCreateView(APIView):
    required_modules = ('inventory',)

    def get(self, request):
        active = _parse_active(request.query_params.get('active'))
        search = request.query_params.get('search', '').strip() or None
        warehouses = _run(ListWarehouses(_repository(request)), search=search, active=active)
        paginator = WarehousePagination()
        page = paginator.paginate_queryset(warehouses, request, view=self)
        return paginator.get_paginated_response(WarehouseSerializer(page, many=True).data)

    def post(self, request):
        serializer = WarehouseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        warehouse = _run(CreateWarehouse(_repository(request)), **serializer.validated_data)
        return Response(WarehouseSerializer(warehouse).data, status=status.HTTP_201_CREATED)


class WarehouseDetailView(APIView):
    required_modules = ('inventory',)

    def get(self, request, warehouse_id):
        warehouse = _run(GetWarehouse(_repository(request)), warehouse_id=warehouse_id)
        return Response(WarehouseSerializer(warehouse).data)

    def patch(self, request, warehouse_id):
        serializer = WarehouseInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        warehouse = _run(UpdateWarehouse(_repository(request)), warehouse_id=warehouse_id,
                         **serializer.validated_data)
        return Response(WarehouseSerializer(warehouse).data)


class WarehouseActivateView(APIView):
    required_modules = ('inventory',)

    def post(self, request, warehouse_id):
        warehouse = _run(ActivateWarehouse(_repository(request)), warehouse_id=warehouse_id)
        return Response(WarehouseSerializer(warehouse).data)


class WarehouseDeactivateView(APIView):
    required_modules = ('inventory',)

    def post(self, request, warehouse_id):
        use_case = DeactivateWarehouse(_repository(request), LedgerWarehouseActivity(company_id_from(request)))
        return Response(WarehouseSerializer(_run(use_case, warehouse_id=warehouse_id)).data)


class WarehouseMakeDefaultView(APIView):
    required_modules = ('inventory',)

    def post(self, request, warehouse_id):
        warehouse = _run(MakeDefaultWarehouse(_repository(request)), warehouse_id=warehouse_id)
        return Response(WarehouseSerializer(warehouse).data)
