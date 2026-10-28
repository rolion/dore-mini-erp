from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.catalog.application.commands import (
    ActivateProduct,
    CreateProduct,
    DeactivateProduct,
    StockControl,
    UpdateProduct,
)
from modules.catalog.application.queries import GetProduct, ListProducts
from modules.catalog.domain.exceptions import ProductNotFound, ProductValidationError, StockHistoryLocked
from modules.catalog.infrastructure.django.repositories import DjangoProductRepository, DjangoUnitRepository
from shared import module_gate, stock_history
from shared.tenancy import company_id_from

from .errors import Conflict
from .pagination import ProductPagination
from .serializers import ProductInputSerializer, ProductSerializer

PRODUCT_NOT_FOUND = 'Producto no encontrado.'


def _repository(request) -> DjangoProductRepository:
    """Repositorio de la empresa del usuario autenticado (nunca de un dato enviado por el cliente)."""
    return DjangoProductRepository(company_id_from(request))


def _stock_control(request) -> StockControl:
    company_id = company_id_from(request)
    return StockControl(
        DjangoUnitRepository(company_id),
        inventory_enabled=module_gate.is_enabled(company_id, 'inventory'),
        has_history=lambda product_id: stock_history.has_history(company_id, product_id),
    )


def _run(use_case, **kwargs):
    """Ejecuta un caso de uso traduciendo errores de dominio a respuestas HTTP."""
    try:
        return use_case.execute(**kwargs)
    except ProductValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except ProductNotFound as exc:
        raise NotFound(PRODUCT_NOT_FOUND) from exc
    except StockHistoryLocked as exc:
        raise Conflict(str(exc), 'stock_history_locked') from exc


def _parse_flag(raw: str | None, field: str) -> bool | None:
    if raw is None or raw == '':
        return None
    if raw in ('true', 'false'):
        return raw == 'true'
    raise ValidationError({field: ['Valor inválido: use "true" o "false".']})


def _parse_active(raw: str | None) -> bool | None:
    return _parse_flag(raw, 'active')


class ProductListCreateView(APIView):
    required_modules = ('catalog',)
    def get(self, request):
        active = _parse_active(request.query_params.get('active'))
        search = request.query_params.get('search', '').strip() or None
        tracks_stock = _parse_flag(request.query_params.get('tracks_stock'), 'tracks_stock')
        products = ListProducts(_repository(request)).execute(search=search, active=active, tracks_stock=tracks_stock)
        paginator = ProductPagination()
        page = paginator.paginate_queryset(products, request, view=self)
        return paginator.get_paginated_response(ProductSerializer(page, many=True).data)

    def post(self, request):
        serializer = ProductInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = _run(CreateProduct(_repository(request), _stock_control(request)), **serializer.validated_data)
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)


class ProductDetailView(APIView):
    required_modules = ('catalog',)
    def get(self, request, product_id):
        product = _run(GetProduct(_repository(request)), product_id=product_id)
        return Response(ProductSerializer(product).data)

    def patch(self, request, product_id):
        serializer = ProductInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = _run(UpdateProduct(_repository(request), _stock_control(request)), product_id=product_id,
                       **serializer.validated_data)
        return Response(ProductSerializer(product).data)


class ProductActivateView(APIView):
    required_modules = ('catalog',)
    def post(self, request, product_id):
        product = _run(ActivateProduct(_repository(request)), product_id=product_id)
        return Response(ProductSerializer(product).data)


class ProductDeactivateView(APIView):
    required_modules = ('catalog',)
    def post(self, request, product_id):
        product = _run(DeactivateProduct(_repository(request)), product_id=product_id)
        return Response(ProductSerializer(product).data)
