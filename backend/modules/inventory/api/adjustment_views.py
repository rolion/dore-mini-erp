from decimal import Decimal
from uuid import UUID

from rest_framework import serializers, status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.inventory.application.adjustment_use_cases import (
    ConfirmAdjustment,
    GetAdjustment,
    GetAdjustmentBalance,
    ListAdjustments,
)
from modules.inventory.domain.adjustment import StockAdjustment
from modules.inventory.domain.exceptions import (
    AdjustmentConflict,
    AdjustmentNotFound,
    AdjustmentValidationError,
    BalanceChanged,
    InsufficientStock,
    WarehouseNotFound,
)
from modules.inventory.domain.repositories import AdjustmentFilters
from modules.inventory.infrastructure.adapters import CatalogProductDirectory, ModularityInventoryPolicy
from modules.inventory.infrastructure.django.adjustment_repository import DjangoStockAdjustmentRepository
from modules.inventory.infrastructure.django.movement_repository import DjangoStockMovementRepository
from modules.inventory.infrastructure.django.repositories import DjangoWarehouseRepository
from shared.tenancy import company_id_from

from .insufficient_stock import InsufficientStockConflict
from .movement_filters import parse_movement_filters
from .pagination import WarehousePagination
from .stock_serializers import RawQuantityField
from .stock_views import _parse_uuid, _unit
from .views import WAREHOUSE_NOT_FOUND, Conflict

ADJUSTMENT_NOT_FOUND = 'Ajuste no encontrado.'
PRODUCT_NOT_FOUND = 'Producto no encontrado.'
DECIMALS = Decimal('0.0001')


class AdjustmentPagination(WarehousePagination):
    page_size = 25


class AdjustmentInputSerializer(serializers.Serializer):
    """Valida forma y tipos; las reglas de negocio (cantidad, motivo, saldo) las aplica el dominio."""

    adjustment_id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    warehouse_id = serializers.UUIDField()
    counted_quantity = RawQuantityField()
    expected_system_quantity = RawQuantityField()
    reason = serializers.CharField(allow_blank=True, trim_whitespace=False, max_length=2000)


class BalanceChangedConflict(APIException):
    """409 `balance_changed` con el saldo vigente."""

    status_code = status.HTTP_409_CONFLICT

    def __init__(self, exc: BalanceChanged):
        super().__init__({'detail': str(exc), 'code': exc.code, 'current_balance': _decimal(exc.current_balance)})


def _decimal(value) -> str:
    return format(value.quantize(DECIMALS), 'f')


class AdjustmentPresenter:
    """Arma la representación de lectura: nombres de producto y almacén, unidad y sentido."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self.warehouses = {w.id: w.name for w in DjangoWarehouseRepository(company_id).list()}
        self._products: dict = {}

    def load_products(self, adjustments: list[StockAdjustment]) -> None:
        self._products = CatalogProductDirectory(self.company_id).get_products(
            {a.product_id for a in adjustments})

    def present(self, adjustment: StockAdjustment, *, detail: bool = False) -> dict:
        product = self._products.get(adjustment.product_id)
        data = {
            'id': adjustment.id,
            'reference': adjustment.reference,
            'created_at': adjustment.created_at,
            'product': {'id': adjustment.product_id, 'name': product.name if product else ''},
            'warehouse': {'id': adjustment.warehouse_id, 'name': self.warehouses.get(adjustment.warehouse_id, '')},
            'system_quantity': _decimal(adjustment.system_quantity),
            'counted_quantity': _decimal(adjustment.counted_quantity),
            'difference': _decimal(adjustment.difference),
            'kind': adjustment.kind.value,
            'unit': {'abbreviation': product.unit_abbreviation if product else None},
            'user': {'id': adjustment.user_id, 'name': adjustment.user_name},
            'status': adjustment.status.value,
        }
        if detail:
            data.update({'reason': adjustment.reason, 'movement': {'id': adjustment.movement_id}})
        return data


def parse_adjustment_filters(params) -> AdjustmentFilters:
    """Reutiliza el parseo de filtros de movimientos (fechas, UUID, rango); los inválidos dan 400 por parámetro."""
    parsed = parse_movement_filters(params)
    return AdjustmentFilters(
        date_from=parsed.date_from, date_to=parsed.date_to, product_id=parsed.product_id,
        warehouse_id=parsed.warehouse_id)


class StockAdjustmentListCreateView(APIView):
    required_modules = ('inventory',)

    def get(self, request):
        company_id = company_id_from(request)
        filters = parse_adjustment_filters(request.query_params)
        adjustments = ListAdjustments(DjangoStockAdjustmentRepository(company_id)).execute(filters)
        paginator = AdjustmentPagination()
        page = paginator.paginate_queryset(adjustments, request, view=self)
        presenter = AdjustmentPresenter(company_id)
        presenter.load_products(page)
        return paginator.get_paginated_response([presenter.present(a) for a in page])

    def post(self, request):
        serializer = AdjustmentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        company_id = company_id_from(request)
        use_case = ConfirmAdjustment(
            DjangoStockMovementRepository(company_id), DjangoStockAdjustmentRepository(company_id),
            DjangoWarehouseRepository(company_id), CatalogProductDirectory(company_id),
            ModularityInventoryPolicy(company_id))
        user = request.user
        try:
            adjustment, created = use_case.execute(
                adjustment_id=data['adjustment_id'], product_id=data['product_id'],
                warehouse_id=data['warehouse_id'], counted_quantity=data['counted_quantity'],
                expected_system_quantity=data['expected_system_quantity'], reason=data['reason'],
                user_id=user.pk, user_name=user.get_full_name().strip() or user.get_username())
        except AdjustmentValidationError as exc:
            raise ValidationError(exc.errors) from exc
        except WarehouseNotFound as exc:
            raise NotFound(WAREHOUSE_NOT_FOUND) from exc
        except InsufficientStock as exc:
            raise InsufficientStockConflict(exc, company_id) from exc
        except BalanceChanged as exc:
            raise BalanceChangedConflict(exc) from exc
        except AdjustmentConflict as exc:
            raise Conflict(str(exc), exc.code) from exc
        presenter = AdjustmentPresenter(company_id)
        presenter.load_products([adjustment])
        return Response(presenter.present(adjustment, detail=True),
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class StockAdjustmentDetailView(APIView):
    required_modules = ('inventory',)

    def get(self, request, adjustment_id):
        company_id = company_id_from(request)
        try:
            adjustment = GetAdjustment(DjangoStockAdjustmentRepository(company_id)).execute(adjustment_id)
        except AdjustmentNotFound as exc:
            raise NotFound(ADJUSTMENT_NOT_FOUND) from exc
        presenter = AdjustmentPresenter(company_id)
        presenter.load_products([adjustment])
        return Response(presenter.present(adjustment, detail=True))


class StockAdjustmentBalanceView(APIView):
    """Saldo vigente del producto en el almacén (0 sin movimientos) y su unidad, para el formulario."""

    required_modules = ('inventory',)

    def get(self, request):
        ids = {}
        for name in ('product_id', 'warehouse_id'):
            raw = request.query_params.get(name)
            if not raw:
                raise ValidationError({name: ['Este campo es obligatorio.']})
            ids[name] = _parse_uuid(raw, name)
        company_id = company_id_from(request)
        if DjangoWarehouseRepository(company_id).get(ids['warehouse_id']) is None:
            raise NotFound(WAREHOUSE_NOT_FOUND)
        product = CatalogProductDirectory(company_id).get_products([ids['product_id']]).get(ids['product_id'])
        if product is None:
            raise NotFound(PRODUCT_NOT_FOUND)
        balance = GetAdjustmentBalance(DjangoStockMovementRepository(company_id)).execute(
            ids['product_id'], ids['warehouse_id'])
        return Response({'system_quantity': _decimal(balance), 'unit': _unit(product)})
