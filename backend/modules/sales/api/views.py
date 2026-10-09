from uuid import UUID

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.sales.application.commands import (
    AddOrderItem,
    ApplyOrderDiscount,
    CancelOrder,
    ChangeOrderItemQuantity,
    CreateOrder,
    DeliverOrder,
    MarkOrderReady,
    RegisterPayment,
    RemoveOrderItem,
    StartOrderPreparation,
    UpdateOrder,
)
from modules.sales.application.queries import GetOrder, ListOrders
from modules.sales.domain.exceptions import (
    OrderItemNotFound,
    OrderNotFound,
    OrderRuleViolation,
    OrderValidationError,
)
from modules.sales.infrastructure.adapters import CustomerDirectoryAdapter, ProductCatalogAdapter, SystemClock
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository

from .filters import parse_order_filters
from .pagination import OrderPagination
from .serializers import (
    CancelSerializer,
    DeliverSerializer,
    DiscountSerializer,
    OrderInputSerializer,
    OrderItemCreateSerializer,
    OrderItemUpdateSerializer,
    OrderSerializer,
    OrderSummarySerializer,
    PaymentInputSerializer,
)

ORDER_NOT_FOUND = 'Pedido no encontrado.'
ITEM_NOT_FOUND = 'Ítem no encontrado.'


class RuleConflict(APIException):
    """409 con `{code, detail}`: el pedido no admite la acción en su estado actual."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Conflicto con el estado del pedido.'


def _uuid(raw: str, message: str) -> UUID:
    """Los ids mal formados responden 404 con `{detail}`, igual que los inexistentes."""
    try:
        return UUID(raw)
    except ValueError:
        raise NotFound(message) from None


def _run(use_case, mutates: bool = True, **kwargs):
    """Ejecuta un caso de uso traduciendo errores de dominio a HTTP.

    Las mutaciones corren dentro de una transacción: el repositorio bloquea la fila del pedido con
    `select_for_update`, que exige transacción abierta, y así se serializan escrituras concurrentes.
    """
    try:
        if mutates:
            with transaction.atomic():
                return use_case.execute(**kwargs)
        return use_case.execute(**kwargs)
    except OrderValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except OrderRuleViolation as exc:
        raise RuleConflict({'code': exc.code, 'detail': exc.message}) from exc
    except OrderNotFound as exc:
        raise NotFound(ORDER_NOT_FOUND) from exc
    except OrderItemNotFound as exc:
        raise NotFound(ITEM_NOT_FOUND) from exc


def _repository() -> DjangoOrderRepository:
    return DjangoOrderRepository()


def _order_response(order, http_status: int = status.HTTP_200_OK) -> Response:
    names = CustomerDirectoryAdapter().get_customer_names([order.customer_id] if order.customer_id else [])
    return Response(OrderSerializer(order, context={'customer_names': names}).data, status=http_status)


def _validated(serializer_class, data, partial: bool = False) -> dict:
    serializer = serializer_class(data=data, partial=partial)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class OrderListCreateView(APIView):
    def get(self, request):
        filters = parse_order_filters(request.query_params)
        summaries = _run(ListOrders(_repository()), mutates=False, filters=filters)
        paginator = OrderPagination()
        page = paginator.paginate_queryset(summaries, request, view=self)
        names = CustomerDirectoryAdapter().get_customer_names({o.customer_id for o in page if o.customer_id})
        data = OrderSummarySerializer(page, many=True, context={'customer_names': names}).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        data = _validated(OrderInputSerializer, request.data)
        order = _run(CreateOrder(_repository(), CustomerDirectoryAdapter(), SystemClock()), **data)
        return _order_response(order, status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    def get(self, request, order_id):
        order = _run(GetOrder(_repository()), mutates=False, order_id=_uuid(order_id, ORDER_NOT_FOUND))
        return _order_response(order)

    def patch(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(OrderInputSerializer, request.data, partial=True)
        order = _run(UpdateOrder(_repository(), CustomerDirectoryAdapter()), order_id=order_id, **data)
        return _order_response(order)


class OrderItemListView(APIView):
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(OrderItemCreateSerializer, request.data)
        order = _run(AddOrderItem(_repository(), ProductCatalogAdapter()), order_id=order_id, **data)
        return _order_response(order, status.HTTP_201_CREATED)


class OrderItemDetailView(APIView):
    def patch(self, request, order_id, item_id):
        order_id, item_id = _uuid(order_id, ORDER_NOT_FOUND), _uuid(item_id, ITEM_NOT_FOUND)
        data = _validated(OrderItemUpdateSerializer, request.data)
        order = _run(ChangeOrderItemQuantity(_repository()), order_id=order_id, item_id=item_id, **data)
        return _order_response(order)

    def delete(self, request, order_id, item_id):
        order_id, item_id = _uuid(order_id, ORDER_NOT_FOUND), _uuid(item_id, ITEM_NOT_FOUND)
        order = _run(RemoveOrderItem(_repository()), order_id=order_id, item_id=item_id)
        return _order_response(order)


class OrderDiscountView(APIView):
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(DiscountSerializer, request.data)
        return _order_response(_run(ApplyOrderDiscount(_repository()), order_id=order_id, **data))


class OrderPrepareView(APIView):
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        return _order_response(_run(StartOrderPreparation(_repository()), order_id=order_id))


class OrderReadyView(APIView):
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        return _order_response(_run(MarkOrderReady(_repository()), order_id=order_id))


class OrderDeliverView(APIView):
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(DeliverSerializer, request.data)
        return _order_response(_run(DeliverOrder(_repository(), SystemClock()), order_id=order_id, **data))


class OrderCancelView(APIView):
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(CancelSerializer, request.data)
        return _order_response(_run(CancelOrder(_repository(), SystemClock()), order_id=order_id, **data))


class OrderPaymentView(APIView):
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(PaymentInputSerializer, request.data)
        order = _run(RegisterPayment(_repository(), SystemClock()), order_id=order_id, **data)
        return _order_response(order, status.HTTP_201_CREATED)
