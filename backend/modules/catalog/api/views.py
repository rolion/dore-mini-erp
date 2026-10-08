from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.catalog.application.commands import (
    ActivateProduct,
    CreateProduct,
    DeactivateProduct,
    UpdateProduct,
)
from modules.catalog.application.queries import GetProduct, ListProducts
from modules.catalog.domain.exceptions import ProductNotFound, ProductValidationError
from modules.catalog.infrastructure.django.repositories import DjangoProductRepository

from .pagination import ProductPagination
from .serializers import ProductInputSerializer, ProductSerializer

PRODUCT_NOT_FOUND = 'Producto no encontrado.'


def _run(use_case, **kwargs):
    """Ejecuta un caso de uso traduciendo errores de dominio a respuestas HTTP."""
    try:
        return use_case.execute(**kwargs)
    except ProductValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except ProductNotFound as exc:
        raise NotFound(PRODUCT_NOT_FOUND) from exc


def _parse_active(raw: str | None) -> bool | None:
    if raw is None or raw == '':
        return None
    if raw in ('true', 'false'):
        return raw == 'true'
    raise ValidationError({'active': ['Valor inválido: use "true" o "false".']})


class ProductListCreateView(APIView):
    def get(self, request):
        active = _parse_active(request.query_params.get('active'))
        search = request.query_params.get('search', '').strip() or None
        products = ListProducts(DjangoProductRepository()).execute(search=search, active=active)
        paginator = ProductPagination()
        page = paginator.paginate_queryset(products, request, view=self)
        return paginator.get_paginated_response(ProductSerializer(page, many=True).data)

    def post(self, request):
        serializer = ProductInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = _run(CreateProduct(DjangoProductRepository()), **serializer.validated_data)
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)


class ProductDetailView(APIView):
    def get(self, request, product_id):
        product = _run(GetProduct(DjangoProductRepository()), product_id=product_id)
        return Response(ProductSerializer(product).data)

    def patch(self, request, product_id):
        serializer = ProductInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = _run(UpdateProduct(DjangoProductRepository()), product_id=product_id,
                       **serializer.validated_data)
        return Response(ProductSerializer(product).data)


class ProductActivateView(APIView):
    def post(self, request, product_id):
        product = _run(ActivateProduct(DjangoProductRepository()), product_id=product_id)
        return Response(ProductSerializer(product).data)


class ProductDeactivateView(APIView):
    def post(self, request, product_id):
        product = _run(DeactivateProduct(DjangoProductRepository()), product_id=product_id)
        return Response(ProductSerializer(product).data)
