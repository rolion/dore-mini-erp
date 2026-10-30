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
from modules.sales.application.delivery import PreviewOrderDelivery
from modules.sales.application.ports import Actor
from modules.sales.application.queries import GetOrder, ListOrders
from modules.sales.domain.exceptions import (
    InsufficientStockForDelivery,
    OrderItemNotFound,
    OrderNotFound,
    OrderRuleViolation,
    OrderValidationError,
)
from modules.sales.infrastructure.adapters import (
    CustomerDirectoryAdapter,
    ProductCatalogAdapter,
    SalesSettingsAdapter,
    StockOutputAdapter,
    SystemClock,
)
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository
from shared.tenancy import company_id_from

from .filters import parse_order_filters
from .pagination import OrderPagination
from .serializers import (
    CancelSerializer,
    DeliverSerializer,
    DeliveryPreviewQuerySerializer,
    DiscountSerializer,
    OrderInputSerializer,
    OrderItemCreateSerializer,
    OrderItemUpdateSerializer,
    OrderSerializer,
    OrderSummarySerializer,
    PaymentInputSerializer,
    delivery_preview_data,
    quantity_text,
)

ORDER_NOT_FOUND = 'Pedido no encontrado.'
ITEM_NOT_FOUND = 'Ítem no encontrado.'
CUSTOMERS_DISABLED = 'El módulo Clientes no está habilitado.'


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
    except InsufficientStockForDelivery as exc:
        raise RuleConflict(_insufficient_stock_body(exc)) from exc
    except OrderRuleViolation as exc:
        raise RuleConflict({'code': exc.code, 'detail': exc.message}) from exc
    except OrderNotFound as exc:
        raise NotFound(ORDER_NOT_FOUND) from exc
    except OrderItemNotFound as exc:
        raise NotFound(ITEM_NOT_FOUND) from exc


def _insufficient_stock_body(exc: InsufficientStockForDelivery) -> dict:
    """409 `insufficient_stock`: almacén y todas las líneas sin saldo (misma forma que el 409 de Inventario)."""
    lines = [{
        'product': {'id': str(line.product_id), 'name': line.product_name},
        'unit': {'abbreviation': line.unit},
        'requested': quantity_text(line.requested),
        'available': quantity_text(line.available),
    } for line in exc.lines]
    return {'code': exc.code, 'detail': exc.message,
            'warehouse': {'id': str(exc.warehouse_id), 'name': exc.warehouse_name}, 'lines': lines}


def _repository(request) -> DjangoOrderRepository:
    """Repositorio de la empresa del usuario autenticado (nunca de un dato enviado por el cliente)."""
    return DjangoOrderRepository(company_id_from(request))


def _customers(request) -> CustomerDirectoryAdapter:
    return CustomerDirectoryAdapter(company_id_from(request))


def _products(request) -> ProductCatalogAdapter:
    return ProductCatalogAdapter(company_id_from(request))


def _stock(request) -> StockOutputAdapter:
    return StockOutputAdapter(company_id_from(request))


def _actor(request) -> Actor:
    user = request.user
    return Actor(user.pk, user.get_full_name().strip() or user.get_username())


def _customer_context(request, customer_ids) -> dict:
    """Nombres de clientes para los serializers; con Clientes deshabilitado `customers_available` es falso."""
    customers = _customers(request)
    return {'customer_names': customers.get_customer_names(customer_ids), 'customers_available': customers.is_available()}


def _order_response(request, order, http_status: int = status.HTTP_200_OK) -> Response:
    context = _customer_context(request, [order.customer_id] if order.customer_id else [])
    if order.status.value == 'DELIVERED':
        context['stock_output'] = _stock(request).output_for(order.id)
    return Response(OrderSerializer(order, context=context).data, status=http_status)


def _validated(serializer_class, data, partial: bool = False) -> dict:
    serializer = serializer_class(data=data, partial=partial)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class OrderListCreateView(APIView):
    required_modules = ('sales',)
    def get(self, request):
        filters = parse_order_filters(request.query_params)
        if filters.customer_id is not None and not _customers(request).is_available():
            raise ValidationError({'customer_id': [CUSTOMERS_DISABLED]})
        summaries = _run(ListOrders(_repository(request)), mutates=False, filters=filters)
        paginator = OrderPagination()
        page = paginator.paginate_queryset(summaries, request, view=self)
        context = _customer_context(request, {o.customer_id for o in page if o.customer_id})
        data = OrderSummarySerializer(page, many=True, context=context).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        data = _validated(OrderInputSerializer, request.data)
        order = _run(CreateOrder(_repository(request), _customers(request), SystemClock()), **data)
        return _order_response(request, order, status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    required_modules = ('sales',)
    def get(self, request, order_id):
        order = _run(GetOrder(_repository(request)), mutates=False, order_id=_uuid(order_id, ORDER_NOT_FOUND))
        return _order_response(request, order)

    def patch(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(OrderInputSerializer, request.data, partial=True)
        order = _run(UpdateOrder(_repository(request), _customers(request)), order_id=order_id, **data)
        return _order_response(request, order)


class OrderItemListView(APIView):
    required_modules = ('sales',)
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(OrderItemCreateSerializer, request.data)
        order = _run(AddOrderItem(_repository(request), _products(request)), order_id=order_id, **data)
        return _order_response(request, order, status.HTTP_201_CREATED)


class OrderItemDetailView(APIView):
    required_modules = ('sales',)
    def patch(self, request, order_id, item_id):
        order_id, item_id = _uuid(order_id, ORDER_NOT_FOUND), _uuid(item_id, ITEM_NOT_FOUND)
        data = _validated(OrderItemUpdateSerializer, request.data)
        order = _run(ChangeOrderItemQuantity(_repository(request)), order_id=order_id, item_id=item_id, **data)
        return _order_response(request, order)

    def delete(self, request, order_id, item_id):
        order_id, item_id = _uuid(order_id, ORDER_NOT_FOUND), _uuid(item_id, ITEM_NOT_FOUND)
        order = _run(RemoveOrderItem(_repository(request)), order_id=order_id, item_id=item_id)
        return _order_response(request, order)


class OrderDiscountView(APIView):
    required_modules = ('sales',)
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(DiscountSerializer, request.data)
        use_case = ApplyOrderDiscount(_repository(request), SalesSettingsAdapter(company_id_from(request)))
        return _order_response(request, _run(use_case, order_id=order_id, **data))


class OrderPrepareView(APIView):
    required_modules = ('sales',)
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        return _order_response(request, _run(StartOrderPreparation(_repository(request)), order_id=order_id))


class OrderReadyView(APIView):
    required_modules = ('sales',)
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        return _order_response(request, _run(MarkOrderReady(_repository(request)), order_id=order_id))


class OrderDeliverView(APIView):
    required_modules = ('sales',)
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(DeliverSerializer, request.data)
        use_case = DeliverOrder(_repository(request), SystemClock(), _stock(request))
        return _order_response(request, _run(use_case, order_id=order_id, actor=_actor(request), **data))


class OrderDeliveryPreviewView(APIView):
    """Vista previa informativa de la entrega: almacenes, existencias y saldo proyectado. No escribe nada."""

    required_modules = ('sales',)

    def get(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        query = _validated(DeliveryPreviewQuerySerializer, request.query_params)
        use_case = PreviewOrderDelivery(_repository(request), _stock(request))
        preview = _run(use_case, mutates=False, order_id=order_id, warehouse_id=query.get('warehouse_id'))
        return Response(delivery_preview_data(preview))


class OrderCancelView(APIView):
    required_modules = ('sales',)
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(CancelSerializer, request.data)
        return _order_response(request, _run(CancelOrder(_repository(request), SystemClock()), order_id=order_id, **data))


class OrderPaymentView(APIView):
    required_modules = ('sales',)
    def post(self, request, order_id):
        order_id = _uuid(order_id, ORDER_NOT_FOUND)
        data = _validated(PaymentInputSerializer, request.data)
        order = _run(RegisterPayment(_repository(request), SystemClock()), order_id=order_id, **data)
        return _order_response(request, order, status.HTTP_201_CREATED)
