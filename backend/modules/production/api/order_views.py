from datetime import date
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.production.application.orders import Actor, ProductionOrders
from modules.production.domain.production_order import (
    InsufficientIngredients, OrderNotFound, OrderStateError, OrderStatus, OrderValidationError, RefrigerationRejected,
    ReleaseTooEarly)
from modules.production.infrastructure.adapters import (
    CatalogProducts, CostingGateway, InventoryLots, InventoryStock, InventoryWarehouses, ModularityReleasePolicy)
from modules.production.infrastructure.django.packing_repository import DjangoPackingRepository
from modules.production.domain.packing import LABELS_PER_PACK, SUGGESTED_BAG_PER_PACK, UNITS_PER_PACK
from modules.production.infrastructure.django.order_repository import DjangoProductionOrderRepository
from modules.production.infrastructure.django.repositories import DjangoRecipeRepository
from shared.tenancy import company_id_from

from .order_serializers import (
    OrderCreateSerializer, OrderPackSerializer, OrderRefrigerateSerializer, OrderUpdateSerializer)
from .views import RecipePagination


class OrderStateConflict(APIException):
    status_code = 409
    default_detail = 'La orden no está en el estado que exige la operación.'
    default_code = 'order_state'


class InsufficientIngredientsConflict(APIException):
    """409 `insufficient_stock` con todas las líneas faltantes."""

    status_code = 409

    def __init__(self, exc: InsufficientIngredients):
        super().__init__({
            'detail': str(exc), 'code': 'insufficient_stock',
            'shortages': [{'product_id': str(s.product_id), 'product_name': s.product_name,
                           'unit_abbreviation': s.unit_abbreviation, 'requested': _qty(s.requested),
                           'available': _qty(s.available), 'missing': _qty(s.missing)} for s in exc.shortages]})


class RefrigerationConflict(APIException):
    status_code = 409

    def __init__(self, exc: RefrigerationRejected):
        super().__init__({'detail': str(exc), 'code': exc.code})


class ReleaseTooEarlyConflict(APIException):
    status_code = 409

    def __init__(self, exc: ReleaseTooEarly):
        super().__init__({'detail': str(exc), 'code': 'release_too_early',
                          'releasable_from': exc.releasable_from.isoformat(), 'min_hours': exc.min_hours})


def _qty(value) -> str:
    return f'{value:.4f}'


def _orders(request) -> ProductionOrders:
    company_id = company_id_from(request)
    return ProductionOrders(DjangoProductionOrderRepository(company_id), DjangoRecipeRepository(company_id),
                            CatalogProducts(company_id), InventoryWarehouses(company_id),
                            stock=InventoryStock(company_id), costs=CostingGateway(company_id),
                            policy=ModularityReleasePolicy(company_id),
                            packings=DjangoPackingRepository(company_id))


def _release(order, min_hours: int, now) -> dict | None:
    """Datos para decidir la liberación; la autoridad es el backend (la acción la vuelve a validar)."""
    if order.status not in (OrderStatus.REFRIGERATING, OrderStatus.READY_TO_PACK):
        return None
    first = order.releasable_from(min_hours)
    return {'min_hours': min_hours, 'releasable_from': first,
            'can_release': order.status == OrderStatus.REFRIGERATING and first is not None and now >= first}


def _packing(company_id, order) -> dict | None:
    """Saldo a granel e historial de empaques; solo para la orden lista para empacar (detalle)."""
    if order.status != OrderStatus.READY_TO_PACK:
        return None
    return {
        'units_per_pack': UNITS_PER_PACK, 'suggested_bag_per_pack': f'{SUGGESTED_BAG_PER_PACK:.4f}',
        'labels_per_pack': LABELS_PER_PACK,
        'bulk_available': _qty(InventoryStock(company_id).lot_available(order)),
        'bulk_unit_abbreviation': order.result_unit_abbreviation,
        'packings': [{
            'id': p.id, 'request_id': p.request_id, 'number': p.number, 'packs': p.packs,
            'pack_product': {'id': p.pack_product_id, 'name': p.pack_product_name},
            'bag_product': {'id': p.bag_product_id, 'name': p.bag_product_name},
            'label_product': ({'id': p.label_product_id, 'name': p.label_product_name}
                              if p.label_product_id else None),
            'bulk_quantity': _qty(p.bulk_quantity), 'bags_quantity': _qty(p.bags_quantity),
            'bag_per_pack': _qty(p.bag_per_pack),
            'labels_quantity': _qty(p.labels_quantity),
            'lot': {'id': p.lot_id, 'code': p.lot_code},
            'cost_total': f'{p.cost_total:.2f}' if p.cost_total is not None else None,
            'unit_cost': f'{p.unit_cost:.6f}' if p.unit_cost is not None else None,
            'created_at': p.created_at, 'created_by': p.created_by_name or None,
        } for p in DjangoPackingRepository(company_id).list(order.id)]}


def _lot(order, record) -> dict:
    """Lote con su saldo de Inventario (físico y disponible para empaque); `null` si el lote ya no existe."""
    return {'id': order.lot_id, 'code': order.lot_code,
            'status': record.status if record else None,
            'physical_quantity': _qty(record.physical_quantity) if record else None,
            'available_quantity': _qty(record.available_quantity) if record else None}


def _serialize(request, orders: list, *, detail: bool = False) -> list[dict]:
    company_id = company_id_from(request)
    names = InventoryWarehouses(company_id).names({order.warehouse_id for order in orders})
    min_hours = ModularityReleasePolicy(company_id).min_refrigeration_hours()
    lots = InventoryLots(company_id).positions([o.lot_id for o in orders if o.lot_id])
    now = timezone.now()
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
            'actual_quantity': _qty(line.actual_quantity) if line.actual_quantity is not None else None,
        } for line in order.ingredients],
        'created_at': order.created_at,
        'started_at': order.started_at,
        'actual_output': _qty(order.actual_output) if order.actual_output is not None else None,
        'entered_at': order.entered_at,
        'refrigerated_at': order.refrigerated_at,
        'lot': _lot(order, lots.get(order.lot_id)) if order.lot_id else None,
        'cost_total': f'{order.cost_total:.2f}' if order.cost_total is not None else None,
        'release': _release(order, min_hours, now),
        'released_at': order.released_at,
        'released_by': order.released_by_name or None,
        'packing': _packing(company_id, order) if detail else None,
    } for order in orders]


def _run(request, callback, **values):
    try:
        with transaction.atomic():
            order = callback(**values)
        return _serialize(request, [order], detail=True)[0]
    except OrderNotFound as exc:
        raise NotFound('Orden de producción no encontrada.') from exc
    except OrderValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except OrderStateError as exc:
        raise OrderStateConflict(str(exc)) from exc
    except InsufficientIngredients as exc:
        raise InsufficientIngredientsConflict(exc) from exc
    except RefrigerationRejected as exc:
        raise RefrigerationConflict(exc) from exc
    except ReleaseTooEarly as exc:
        raise ReleaseTooEarlyConflict(exc) from exc


def _values(serializer_class, request) -> dict:
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    return {**data, 'preparations': data.get('preparations')}


def _list_filters(params) -> dict:
    """`recipe_id`, `date_from` y `date_to` opcionales; un valor mal formado responde 400 con el campo."""
    errors: dict = {}
    values: dict = {}
    if params.get('recipe_id'):
        try:
            values['recipe_id'] = UUID(params['recipe_id'])
        except ValueError:
            errors['recipe_id'] = ['Receta no válida.']
    for key in ('date_from', 'date_to'):
        if params.get(key):
            try:
                values[key] = date.fromisoformat(params[key])
            except ValueError:
                errors[key] = ['Usa una fecha con formato AAAA-MM-DD.']
    if not errors and values.get('date_from') and values.get('date_to') and values['date_from'] > values['date_to']:
        errors['date_from'] = ['La fecha inicial no puede ser posterior a la final.']
    if errors:
        raise ValidationError(errors)
    return values


class OrderListCreateView(APIView):
    required_modules = ('production',)

    def get(self, request):
        status = request.query_params.get('status', 'all')
        if status != 'all' and status not in OrderStatus.ALL:
            raise ValidationError({'status': ['Usa all, draft, in_preparation, refrigerating o ready_to_pack.']})
        orders = _orders(request).repository.list(status=status, **_list_filters(request.query_params))
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


class OrderRefrigerateView(APIView):
    required_modules = ('production',)

    def post(self, request, order_id):
        serializer = OrderRefrigerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        actor = Actor(user.pk, user.get_full_name().strip() or user.get_username())
        return Response(_run(request, _orders(request).refrigerate, order_id=order_id,
                             entered_at=data['entered_at'], actual_output=data.get('actual_output'),
                             ingredients=[dict(item) for item in data['ingredients']], actor=actor))


class OrderReleaseView(APIView):
    required_modules = ('production',)

    def post(self, request, order_id):
        user = request.user
        actor = Actor(user.pk, user.get_full_name().strip() or user.get_username())
        return Response(_run(request, _orders(request).release, order_id=order_id, actor=actor))


class OrderPackView(APIView):
    required_modules = ('production',)

    def post(self, request, order_id):
        serializer = OrderPackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        actor = Actor(user.pk, user.get_full_name().strip() or user.get_username())
        created = []

        def pack(**values):
            orders = _orders(request)
            packing, was_created = orders.pack(**values)
            created.append(was_created)
            return orders.get(order_id)

        body = _run(request, pack, order_id=order_id, request_id=data['request_id'], packs=data.get('packs'),
                    pack_product_id=data['pack_product_id'], bag_product_id=data['bag_product_id'], actor=actor,
                    label_product_id=data.get('label_product_id'), bag_per_pack=data.get('bag_per_pack'))
        return Response(body, status=201 if created and created[0] else 200)


class OrderWarehousesView(APIView):
    required_modules = ('production',)

    def get(self, request):
        return Response([{'id': w.id, 'name': w.name, 'is_default': w.is_default}
                         for w in InventoryWarehouses(company_id_from(request)).active()])
