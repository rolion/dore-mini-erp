from django.db import transaction
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.production.application.orders import ProductionOrders
from modules.production.domain.production_order import (
    OrderNotFound, OrderStateError, OrderStatus, OrderValidationError)
from modules.production.infrastructure.adapters import CatalogProducts, InventoryWarehouses
from modules.production.infrastructure.django.order_repository import DjangoProductionOrderRepository
from modules.production.infrastructure.django.repositories import DjangoRecipeRepository
from shared.tenancy import company_id_from

from .order_serializers import OrderCreateSerializer, OrderUpdateSerializer
from .views import RecipePagination


class OrderStateConflict(APIException):
    status_code = 409
    default_detail = 'La orden no está en el estado que exige la operación.'
    default_code = 'order_state'


def _qty(value) -> str:
    return f'{value:.4f}'


def _orders(request) -> ProductionOrders:
    company_id = company_id_from(request)
    return ProductionOrders(DjangoProductionOrderRepository(company_id), DjangoRecipeRepository(company_id),
                            CatalogProducts(company_id), InventoryWarehouses(company_id))


def _serialize(request, orders: list) -> list[dict]:
    names = InventoryWarehouses(company_id_from(request)).names({order.warehouse_id for order in orders})
    return [{
        'id': order.id,
        'number': order.number,
        'status': order.status,
        'recipe': {'id': order.recipe_id, 'name': order.recipe_name},
        'result_product': {'id': order.result_product_id, 'name': order.result_product_name,
                           'unit': ({'id': order.result_unit_id, 'abbreviation': order.result_unit_abbreviation}
                                    if order.result_unit_id else None)},
        'warehouse': {'id': order.warehouse_id, 'name': names.get(order.warehouse_id)},
        'preparations': order.preparations,
        'yield_per_preparation': _qty(order.yield_per_preparation),
        'expected_output': _qty(order.expected_output),
        'ingredients': [{
            'product_id': line.product_id, 'product_name': line.product_name, 'unit_id': line.unit_id,
            'unit_abbreviation': line.unit_abbreviation,
            'quantity_per_preparation': _qty(line.quantity_per_preparation),
            'expected_quantity': _qty(order.expected_quantity(line)),
        } for line in order.ingredients],
        'created_at': order.created_at,
        'started_at': order.started_at,
    } for order in orders]


def _run(request, callback, **values):
    try:
        with transaction.atomic():
            order = callback(**values)
        return _serialize(request, [order])[0]
    except OrderNotFound as exc:
        raise NotFound('Orden de producción no encontrada.') from exc
    except OrderValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except OrderStateError as exc:
        raise OrderStateConflict(str(exc)) from exc


def _values(serializer_class, request) -> dict:
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    return {**data, 'preparations': data.get('preparations')}


class OrderListCreateView(APIView):
    required_modules = ('production',)

    def get(self, request):
        status = request.query_params.get('status', 'all')
        if status != 'all' and status not in OrderStatus.ALL:
            raise ValidationError({'status': ['Usa all, draft o in_preparation.']})
        orders = _orders(request).repository.list(status=status)
        paginator = RecipePagination()
        page = paginator.paginate_queryset(orders, request, view=self)
        return paginator.get_paginated_response(_serialize(request, page))

    def post(self, request):
        return Response(_run(request, _orders(request).create, **_values(OrderCreateSerializer, request)),
                        status=201)


class OrderDetailView(APIView):
    required_modules = ('production',)
    http_method_names = ['get', 'put', 'head', 'options']

    def get(self, request, order_id):
        return Response(_run(request, _orders(request).get, order_id=order_id))

    def put(self, request, order_id):
        return Response(_run(request, _orders(request).update, order_id=order_id,
                             **_values(OrderUpdateSerializer, request)))


class OrderStartView(APIView):
    required_modules = ('production',)

    def post(self, request, order_id):
        return Response(_run(request, _orders(request).start, order_id=order_id))


class OrderWarehousesView(APIView):
    required_modules = ('production',)

    def get(self, request):
        return Response([{'id': w.id, 'name': w.name, 'is_default': w.is_default}
                         for w in InventoryWarehouses(company_id_from(request)).active()])
