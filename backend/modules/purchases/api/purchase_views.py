from uuid import UUID

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.purchases.application.purchase_commands import CreatePurchase, ItemInput, UpdatePurchase
from modules.purchases.application.purchase_queries import GetPurchase, ListPurchases
from modules.purchases.domain.exceptions import PurchaseNotEditable, PurchaseNotFound, PurchaseValidationError
from modules.purchases.infrastructure.adapters import ProductCatalogAdapter
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository
from modules.purchases.infrastructure.django.repositories import DjangoSupplierRepository
from shared.tenancy import company_id_from

from .pagination import SupplierPagination
from .purchase_serializers import PurchaseInputSerializer, purchase_representation, summary_representation

PURCHASE_NOT_FOUND = 'Compra no encontrada.'
NOT_EDITABLE = 'La compra ya no admite cambios.'
REQUIRED_MODULES = ('purchases',)


class NotEditable(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = NOT_EDITABLE


def _purchases(request) -> DjangoPurchaseRepository:
    """Repositorio de la empresa del usuario autenticado (nunca de un dato enviado por el cliente)."""
    return DjangoPurchaseRepository(company_id_from(request))


def _suppliers(request) -> DjangoSupplierRepository:
    return DjangoSupplierRepository(company_id_from(request))


def _items(validated: dict) -> dict:
    """`items` validado -> entradas de la aplicación; si no se envió, se deja fuera (no se tocan las líneas)."""
    if 'items' not in validated:
        return {}
    return {'items': [ItemInput(i['product_id'], i['quantity'], i['unit_price']) for i in validated['items']]}


def _run(callable_, **kwargs):
    """Ejecuta un caso de uso en una transacción (el bloqueo de fila de la edición la exige) traduciendo errores."""
    try:
        with transaction.atomic():
            return callable_(**kwargs)
    except PurchaseValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except PurchaseNotFound as exc:
        raise NotFound(PURCHASE_NOT_FOUND) from exc
    except PurchaseNotEditable as exc:
        raise NotEditable() from exc


def _detail(request, purchase):
    return purchase_representation(GetPurchase(_purchases(request), _suppliers(request)).detail(purchase))


class PurchaseListCreateView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request):
        raw = request.query_params.get('supplier_id')
        try:
            supplier_id = UUID(raw) if raw else None
        except ValueError:
            raise ValidationError({'supplier_id': ['Valor inválido: use un identificador de proveedor.']}) from None
        summaries = ListPurchases(_purchases(request)).execute(supplier_id=supplier_id)
        paginator = SupplierPagination()
        page = paginator.paginate_queryset(summaries, request, view=self)
        return paginator.get_paginated_response([summary_representation(s) for s in page])

    def post(self, request):
        serializer = PurchaseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        use_case = CreatePurchase(_purchases(request), _suppliers(request),
                                  ProductCatalogAdapter(company_id_from(request)))
        data = {k: v for k, v in serializer.validated_data.items() if k != 'items'}
        purchase = _run(use_case.execute, **data, **_items(serializer.validated_data))
        return Response(_detail(request, purchase), status=status.HTTP_201_CREATED)


class PurchaseDetailView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request, purchase_id):
        detail = _run(GetPurchase(_purchases(request), _suppliers(request)).execute, purchase_id=purchase_id)
        return Response(purchase_representation(detail))

    def patch(self, request, purchase_id):
        serializer = PurchaseInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        use_case = UpdatePurchase(_purchases(request), _suppliers(request),
                                  ProductCatalogAdapter(company_id_from(request)))
        data = {k: v for k, v in serializer.validated_data.items() if k != 'items'}
        purchase = _run(use_case.execute, purchase_id=purchase_id, **data, **_items(serializer.validated_data))
        return Response(_detail(request, purchase))
