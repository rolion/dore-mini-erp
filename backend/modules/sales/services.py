"""Fachada pública de solo lectura del módulo Sales para otros módulos (p. ej. Reporting).

Es la única vía de entrada entre módulos: devuelve DTO inmutables, nunca entidades ni modelos.

Definiciones únicas (propiedad de Sales):
- Pedido válido: no cancelado y con al menos un ítem. Toda métrica de ventas sale solo de pedidos válidos.
- Ventas = Σ `total` de pedidos válidos con `order_date` en el rango (inclusive); los pagos no intervienen.
- Pendiente de entrega: pedido válido NEW, IN_PREPARATION o READY.
- Pendiente de cobro: pedido válido con `total − paid_total > 0`, en cualquier estado logístico.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from modules.sales.infrastructure.django import read_queries

ZERO = Decimal('0.00')
DEFAULT_LIMIT = 10


@dataclass(frozen=True)
class SalesTotals:
    total: Decimal
    orders_count: int


@dataclass(frozen=True)
class ChannelSales:
    sales_channel: str
    orders_count: int
    total: Decimal


@dataclass(frozen=True)
class ProductSales:
    product_id: UUID
    product_name: str
    units: int
    amount: Decimal  # Σ subtotal de ítems, antes del descuento del pedido


@dataclass(frozen=True)
class CustomerSales:
    customer_id: UUID
    orders_count: int
    total: Decimal


@dataclass(frozen=True)
class PendingOrder:
    id: UUID
    customer_id: UUID | None
    order_date: date
    expected_delivery_date: date | None
    status: str
    payment_status: str
    total: Decimal
    balance: Decimal


@dataclass(frozen=True)
class PendingOrders:
    count: int
    balance_total: Decimal
    rows: tuple[PendingOrder, ...]


def get_sales_totals(date_from: date, date_to: date) -> SalesTotals:
    result = read_queries.totals(date_from, date_to)
    return SalesTotals(total=result['total'] or ZERO, orders_count=result['orders_count'])


def get_sales_by_channel(date_from: date, date_to: date) -> tuple[ChannelSales, ...]:
    return tuple(
        ChannelSales(sales_channel=row['sales_channel'], orders_count=row['orders_count'], total=row['total'])
        for row in read_queries.by_channel(date_from, date_to)
    )


def get_top_products(date_from: date, date_to: date, limit: int = DEFAULT_LIMIT) -> tuple[ProductSales, ...]:
    """Orden: unidades desc, importe desc, nombre. El nombre es el del snapshot más reciente del rango."""
    rows = read_queries.product_totals(date_from, date_to)
    names = read_queries.latest_product_names(date_from, date_to, [row['product_id'] for row in rows])
    products = [
        ProductSales(product_id=row['product_id'], product_name=names.get(row['product_id'], ''),
                     units=row['units'], amount=row['amount'])
        for row in rows
    ]
    products.sort(key=lambda p: (-p.units, -p.amount, p.product_name, str(p.product_id)))
    return tuple(products[:limit])


def get_top_customers(date_from: date, date_to: date, limit: int = DEFAULT_LIMIT) -> tuple[CustomerSales, ...]:
    """Solo pedidos con cliente; orden: total desc, pedidos desc."""
    return tuple(
        CustomerSales(customer_id=row['customer_id'], orders_count=row['orders_count'], total=row['total'])
        for row in read_queries.customer_totals(date_from, date_to, limit)
    )


def _pending_rows(queryset, limit: int) -> tuple[PendingOrder, ...]:
    return tuple(
        PendingOrder(id=o.id, customer_id=o.customer_id, order_date=o.order_date,
                     expected_delivery_date=o.expected_delivery_date, status=o.status,
                     payment_status=o.payment_status, total=o.total, balance=o.total - o.paid_total)
        for o in queryset[:limit]
    )


def get_pending_delivery(limit: int = DEFAULT_LIMIT) -> PendingOrders:
    """Entrega prevista más próxima primero (sin fecha al final). No depende de ningún periodo."""
    queryset = read_queries.pending_delivery()
    return PendingOrders(count=queryset.count(), balance_total=ZERO, rows=_pending_rows(queryset, limit))


def get_pending_collection(limit: int = DEFAULT_LIMIT) -> PendingOrders:
    """Pedidos con saldo, los más antiguos primero. No depende de ningún periodo."""
    queryset = read_queries.pending_collection()
    return PendingOrders(count=queryset.count(), balance_total=read_queries.collection_balance(queryset) or ZERO,
                         rows=_pending_rows(queryset, limit))
