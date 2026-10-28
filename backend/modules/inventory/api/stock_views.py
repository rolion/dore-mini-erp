from uuid import UUID

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.inventory.application.movement_ports import ProductInfo
from modules.inventory.application.stock_use_cases import CheckOpeningHistory, ListStock, RegisterOpening
from modules.inventory.domain.exceptions import (
    MovementConflict,
    MovementValidationError,
    OpeningIdReused,
    OpeningValidationError,
    StockHistoryExists,
    WarehouseNotFound,
)
from modules.inventory.infrastructure.adapters import CatalogProductDirectory
from modules.inventory.infrastructure.django.movement_repository import DjangoStockMovementRepository
from modules.inventory.infrastructure.django.repositories import DjangoWarehouseRepository
from shared.tenancy import company_id_from

from .pagination import WarehousePagination
from .stock_serializers import (
    OpeningInputSerializer,
    OpeningSerializer,
    StockBalanceSerializer,
)
from .views import WAREHOUSE_NOT_FOUND, Conflict


class StockHistoryConflict(APIException):
    """409 `stock_history_exists` con las líneas (posición y producto) que ya tienen movimientos."""

    status_code = status.HTTP_409_CONFLICT

    def __init__(self, exc: StockHistoryExists):
        super().__init__({
            'detail': str(exc), 'code': 'stock_history_exists',
            'lines': [{'index': index, 'product_id': str(product_id)}
                      for index, product_id in zip(exc.indices, exc.product_ids)],
        })


def _parse_uuid(raw: str, name: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError:
        raise ValidationError({name: ['Debe ser un UUID válido.']}) from None


def _uuid_param(request, name: str, required: bool = True) -> UUID | None:
    raw = request.query_params.get(name)
    if not raw:
        if required:
            raise ValidationError({name: ['Este campo es obligatorio.']})
        return None
    return _parse_uuid(raw, name)


def _by_position(errors: dict, data) -> dict:
    """Los errores de líneas siempre viajan como lista (un dict por línea), igual que los del dominio."""
    lines = errors.get('lines')
    sent = data.get('lines') if hasattr(data, 'get') else None
    # DRF indexa por posición solo cuando se envió una lista; si `lines` no es una lista, su mensaje se deja tal cual.
    if isinstance(lines, dict) and isinstance(sent, list) and all(str(key).isdigit() for key in lines):
        errors = {**errors, 'lines': [lines.get(index, {}) for index in range(len(sent))]}
    return errors


def _unit(info: ProductInfo | None) -> dict | None:
    if info is None or info.unit_abbreviation is None:
        return None
    return {'abbreviation': info.unit_abbreviation, 'allows_fractions': info.allows_fractions}


class OpeningCreateView(APIView):
    required_modules = ('inventory',)

    def post(self, request):
        serializer = OpeningInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(_by_position(serializer.errors, request.data))
        data = serializer.validated_data
        company_id = company_id_from(request)
        use_case = RegisterOpening(
            DjangoStockMovementRepository(company_id), DjangoWarehouseRepository(company_id),
            CatalogProductDirectory(company_id))
        user = request.user
        try:
            outcome = use_case.execute(
                opening_id=data['opening_id'], warehouse_id=data['warehouse_id'],
                movement_date=data['movement_date'], reference=data['reference'],
                lines=[(line['product_id'], line['quantity']) for line in data['lines']],
                today=timezone.localdate(), user_name=user.get_full_name().strip() or user.get_username())
        except OpeningValidationError as exc:
            raise ValidationError(exc.errors) from exc
        except MovementValidationError as exc:
            raise ValidationError(exc.errors) from exc
        except WarehouseNotFound as exc:
            raise NotFound(WAREHOUSE_NOT_FOUND) from exc
        except StockHistoryExists as exc:
            raise StockHistoryConflict(exc) from exc
        except OpeningIdReused as exc:
            raise Conflict(str(exc), 'opening_id_reused') from exc
        except MovementConflict as exc:
            raise Conflict(str(exc), exc.code) from exc
        opening = outcome.opening
        body = {
            'opening_id': opening.opening_id, 'warehouse_id': opening.warehouse_id,
            'movement_date': opening.movement_date, 'reference': opening.reference,
            'lines': [{'product_id': line.product_id, 'quantity': line.quantity,
                       'movement_id': outcome.movement_ids.get(line.product_id)} for line in opening.lines],
        }
        return Response(OpeningSerializer(body).data,
                        status=status.HTTP_200_OK if outcome.replayed else status.HTTP_201_CREATED)


class StockListView(APIView):
    required_modules = ('inventory',)

    def get(self, request):
        warehouse_id = _uuid_param(request, 'warehouse_id', required=False)
        company_id = company_id_from(request)
        balances = ListStock(DjangoStockMovementRepository(company_id)).execute(warehouse_id)
        paginator = WarehousePagination()
        page = paginator.paginate_queryset(balances, request, view=self)
        products = CatalogProductDirectory(company_id).get_products([entry.product_id for entry in page])
        rows = [{
            'product_id': entry.product_id,
            'product_name': products[entry.product_id].name if entry.product_id in products else None,
            'warehouse_id': entry.warehouse_id, 'warehouse_name': entry.warehouse_name,
            'quantity': entry.quantity, 'unit': _unit(products.get(entry.product_id)),
        } for entry in page]
        return paginator.get_paginated_response(StockBalanceSerializer(rows, many=True).data)


class OpeningCheckView(APIView):
    required_modules = ('inventory',)

    def get(self, request):
        warehouse_id = _uuid_param(request, 'warehouse_id')
        product_ids = [_parse_uuid(raw, 'product_id') for raw in request.query_params.getlist('product_id')]
        found = CheckOpeningHistory(DjangoStockMovementRepository(company_id_from(request))).execute(
            warehouse_id, product_ids)
        return Response({'products_with_history': [str(product_id) for product_id in found]})
