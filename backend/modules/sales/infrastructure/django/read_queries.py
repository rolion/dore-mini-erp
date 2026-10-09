"""Consultas de solo lectura sobre las tablas de Sales para otros módulos (a través de `modules/sales/services.py`).

Una sola definición de "pedido válido" para todas las métricas: no cancelado y con al menos un ítem.
"""
from datetime import date

from django.db.models import Count, Exists, F, OuterRef, QuerySet, Sum

from modules.sales.domain.enums import OrderStatus

from .models import OrderItemModel, OrderModel

OPEN_STATUSES = (OrderStatus.NEW.value, OrderStatus.IN_PREPARATION.value, OrderStatus.READY.value)


def valid_orders() -> QuerySet:
    has_items = Exists(OrderItemModel.objects.filter(order=OuterRef('pk')))
    return OrderModel.objects.exclude(status=OrderStatus.CANCELLED.value).filter(has_items)


def valid_orders_between(date_from: date, date_to: date) -> QuerySet:
    return valid_orders().filter(order_date__gte=date_from, order_date__lte=date_to)


def totals(date_from: date, date_to: date) -> dict:
    return valid_orders_between(date_from, date_to).aggregate(total=Sum('total'), orders_count=Count('id'))


def by_channel(date_from: date, date_to: date) -> list[dict]:
    return list(
        valid_orders_between(date_from, date_to)
        .values('sales_channel')
        .annotate(orders_count=Count('id'), total=Sum('total'))
        .order_by('-total', 'sales_channel')
    )


def product_totals(date_from: date, date_to: date) -> list[dict]:
    """Unidades e importe (antes del descuento del pedido) por producto, en pedidos válidos del rango."""
    orders = valid_orders_between(date_from, date_to).values('pk')
    return list(
        OrderItemModel.objects.filter(order__in=orders)
        .values('product_id')
        .annotate(units=Sum('quantity'), amount=Sum('subtotal'))
    )


def latest_product_names(date_from: date, date_to: date, product_ids: list) -> dict:
    """Nombre del snapshot más reciente (por fecha de pedido y alta del ítem) de cada producto."""
    orders = valid_orders_between(date_from, date_to).values('pk')
    rows = (
        OrderItemModel.objects.filter(order__in=orders, product_id__in=product_ids)
        .order_by('-order__order_date', '-created_at', '-id')
        .values_list('product_id', 'product_name')
    )
    names: dict = {}
    for product_id, name in rows:
        names.setdefault(product_id, name)
    return names


def customer_totals(date_from: date, date_to: date, limit: int) -> list[dict]:
    return list(
        valid_orders_between(date_from, date_to)
        .filter(customer_id__isnull=False)
        .values('customer_id')
        .annotate(orders_count=Count('id'), total=Sum('total'))
        .order_by('-total', '-orders_count', 'customer_id')[:limit]
    )


def pending_delivery() -> QuerySet:
    return valid_orders().filter(status__in=OPEN_STATUSES).order_by(
        F('expected_delivery_date').asc(nulls_last=True), 'order_date', 'created_at', 'id')


def pending_collection() -> QuerySet:
    return valid_orders().filter(total__gt=F('paid_total')).order_by('order_date', 'created_at', 'id')


def collection_balance(queryset: QuerySet):
    return queryset.aggregate(balance=Sum(F('total') - F('paid_total')))['balance']
