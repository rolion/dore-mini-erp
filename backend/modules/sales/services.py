"""Fachada pública de solo lectura del módulo Sales para otros módulos (p. ej. Reporting).

Es la única vía de entrada entre módulos: devuelve DTO inmutables, nunca entidades ni modelos.
Toda función recibe la empresa como primer argumento y solo ve los pedidos de esa empresa.

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

from modules.sales.domain.enums import OrderStatus
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


def get_sales_totals(company_id: UUID, date_from: date, date_to: date) -> SalesTotals:
    result = read_queries.totals(company_id, date_from, date_to)
    return SalesTotals(total=result['total'] or ZERO, orders_count=result['orders_count'])


def get_sales_by_channel(company_id: UUID, date_from: date, date_to: date) -> tuple[ChannelSales, ...]:
    return tuple(
        ChannelSales(sales_channel=row['sales_channel'], orders_count=row['orders_count'], total=row['total'])
        for row in read_queries.by_channel(company_id, date_from, date_to)
    )


def get_top_products(company_id: UUID, date_from: date, date_to: date,
                     limit: int = DEFAULT_LIMIT) -> tuple[ProductSales, ...]:
    """Orden: unidades desc, importe desc, nombre. El nombre es el del snapshot más reciente del rango."""
    rows = read_queries.product_totals(company_id, date_from, date_to)
    names = read_queries.latest_product_names(company_id, date_from, date_to, [row['product_id'] for row in rows])
    products = [
        ProductSales(product_id=row['product_id'], product_name=names.get(row['product_id'], ''),
                     units=row['units'], amount=row['amount'])
        for row in rows
    ]
    products.sort(key=lambda p: (-p.units, -p.amount, p.product_name, str(p.product_id)))
    return tuple(products[:limit])


def get_top_customers(company_id: UUID, date_from: date, date_to: date,
                      limit: int = DEFAULT_LIMIT) -> tuple[CustomerSales, ...]:
    """Solo pedidos con cliente; orden: total desc, pedidos desc."""
    return tuple(
        CustomerSales(customer_id=row['customer_id'], orders_count=row['orders_count'], total=row['total'])
        for row in read_queries.customer_totals(company_id, date_from, date_to, limit)
    )


@dataclass(frozen=True)
class CustomerCommercialSummary:
    customer_id: UUID
    order_count: int
    last_purchase_date: date | None
    outstanding_amount: Decimal


def get_customer_commercial_summaries(company_id: UUID, customer_ids) -> dict[UUID, CustomerCommercialSummary]:
    """Pedidos válidos, última compra y saldo (Σ total − pagado, solo con saldo > 0) por cliente de la empresa.

    Los clientes sin pedidos válidos no aparecen en el resultado.
    """
    ids = list(customer_ids)
    if not ids:
        return {}
    return {
        row['customer_id']: CustomerCommercialSummary(
            customer_id=row['customer_id'], order_count=row['orders_count'],
            last_purchase_date=row['last_order_date'], outstanding_amount=row['balance'] or ZERO)
        for row in read_queries.customer_summaries(company_id, ids)
    }


def list_customer_ids_with_orders_in_warehouse(company_id: UUID, warehouse_id: UUID) -> list[UUID]:
    """Clientes con al menos un pedido válido atendido desde el almacén indicado."""
    return read_queries.customer_ids_in_warehouse(company_id, warehouse_id)


def _pending_rows(queryset, limit: int) -> tuple[PendingOrder, ...]:
    return tuple(
        PendingOrder(id=o.id, customer_id=o.customer_id, order_date=o.order_date,
                     expected_delivery_date=o.expected_delivery_date, status=o.status,
                     payment_status=o.payment_status, total=o.total, balance=o.total - o.paid_total)
        for o in queryset[:limit]
    )


def get_pending_delivery(company_id: UUID, limit: int = DEFAULT_LIMIT) -> PendingOrders:
    """Entrega prevista más próxima primero (sin fecha al final). No depende de ningún periodo."""
    queryset = read_queries.pending_delivery(company_id)
    return PendingOrders(count=queryset.count(), balance_total=ZERO, rows=_pending_rows(queryset, limit))


def get_pending_collection(company_id: UUID, limit: int = DEFAULT_LIMIT) -> PendingOrders:
    """Pedidos con saldo, los más antiguos primero. No depende de ningún periodo."""
    queryset = read_queries.pending_collection(company_id)
    return PendingOrders(count=queryset.count(), balance_total=read_queries.collection_balance(queryset) or ZERO,
                         rows=_pending_rows(queryset, limit))


@dataclass(frozen=True)
class HistoricalPayment:
    """Pago de un pedido tal como está guardado. Ventas no guarda autor ni comprobante del cobro."""
    id: UUID
    amount: Decimal
    method: str
    payment_date: date
    document_ref: str  # ID del pedido
    reference: str
    document_state: str  # estado del pedido (p. ej. CANCELLED: el pago conservado sigue siendo dinero recibido)


def list_historical_payments(company_id: UUID, date_from: date | None = None,
                             date_to: date | None = None) -> tuple[HistoricalPayment, ...]:
    """Pagos de la empresa por fecha efectiva (inclusive), también los de pedidos cancelados. Solo lectura."""
    return tuple(
        HistoricalPayment(id=p.id, amount=p.amount, method=p.payment_method, payment_date=p.payment_date,
                          document_ref=str(p.order_id), reference=p.reference, document_state=p.order.status)
        for p in read_queries.payments_between(company_id, date_from, date_to)
    )


# --- Escritura para la importación de ventas (TASK-cargar-ventas-desde-archivo) -----------------------------

@dataclass(frozen=True)
class ImportedSaleLine:
    product_id: UUID
    quantity: int
    unit_price: Decimal  # precio del archivo: la venta histórica conserva su precio, no el del catálogo


@dataclass(frozen=True)
class ImportedSale:
    order_id: UUID
    code: str
    total: Decimal
    without_posting: bool  # la fecha no tiene cobertura contable (o no se pidió contabilizar): sin asiento


def import_delivered_sale(company_id: UUID, *, sale_date: date, sales_channel: str, customer_id: UUID | None,
                          lines: list[ImportedSaleLine], payment_method: str, warehouse_id: UUID | None,
                          user_id: UUID | None, user_name: str, post_accounting: bool = True,
                          notes: str = '', discount: Decimal = Decimal('0')) -> ImportedSale:
    """Registra una venta histórica completa con los casos de uso de Ventas: crea el pedido en su fecha con el
    precio del archivo, lo confirma, lo marca listo, lo entrega (salida de stock, costo y reconocimiento contable) y
    registra el cobro por el total (con el descuento del archivo) en la misma fecha.

    Corre en la transacción de quien llama (todo o nada). Con `post_accounting=False` no genera asientos. Lanza
    `shared.import_errors.ImportRejected` con el mensaje del módulo que rechazó la operación.
    """
    from modules.sales.application.commands import (
        CreateOrder,
        DeliverOrder,
        MarkOrderReady,
        RegisterPayment,
        StartOrderPreparation,
    )
    from modules.sales.application.ports import Actor
    from modules.sales.domain import exceptions as errors
    from modules.sales.infrastructure.adapters import (
        CustomerDirectoryAdapter,
        DeliveryCostingAdapter,
        ProductCatalogAdapter,
        SalesPostingAdapter,
        StockOutputAdapter,
        SystemClock,
    )
    from modules.sales.infrastructure.django.repositories import DjangoOrderRepository
    from shared.import_errors import ImportRejected, first_error

    repository = DjangoOrderRepository(company_id)
    clock = SystemClock()
    actor = Actor(user_id, user_name)
    products = ProductCatalogAdapter(company_id)
    posting = SalesPostingAdapter(company_id) if post_accounting else None
    try:
        order = CreateOrder(repository, CustomerDirectoryAdapter(company_id), clock).execute(
            sales_channel=sales_channel, order_date=sale_date, customer_id=customer_id, notes=notes)
        order = repository.get_for_update(order.id)
        for line in lines:
            product = products.get_product_for_sale(line.product_id)
            if product is None:
                raise ImportRejected('product_missing', 'El producto no existe.', 'product_name')
            if not product.active:
                raise ImportRejected('product_inactive', f'El producto «{product.name}» está inactivo.',
                                     'product_name')
            if not product.can_sell:
                raise ImportRejected('product_not_sellable', f'El producto «{product.name}» no se puede vender.',
                                     'product_name')
            order.add_item(product.id, product.name, line.unit_price, line.quantity)
        if discount:
            order.apply_discount(discount)  # el archivo manda: sin el tope porcentual de la empresa
        order = repository.save(order)
        StartOrderPreparation(repository).execute(order.id)
        MarkOrderReady(repository).execute(order.id)
        DeliverOrder(repository, clock, StockOutputAdapter(company_id), posting,
                     DeliveryCostingAdapter(company_id, post_accounting)).execute(
            order.id, sale_date, warehouse_id, actor)
        order = RegisterPayment(repository, clock, posting).execute(
            order.id, amount=order.total, payment_method=payment_method, payment_date=sale_date, actor=actor)
    except errors.InsufficientStockForDelivery as exc:
        detail = '; '.join(f'{line.product_name}: pides {line.requested}, hay {line.available}' for line in exc.lines)
        raise ImportRejected('insufficient_stock', f'{exc.message} {detail}'.strip(), 'quantity') from exc
    except errors.OrderRuleViolation as exc:
        raise ImportRejected(exc.code, exc.message) from exc
    except errors.OrderValidationError as exc:
        field, message = first_error(exc.errors)
        raise ImportRejected('order_rejected', message, field) from exc
    covered = post_accounting and SalesPostingAdapter(company_id).posts_on(sale_date)
    return ImportedSale(order_id=order.id, code=order.code, total=order.total, without_posting=not covered)


# --- Vínculo de oportunidades de CRM (TASK-crm-prospectos-oportunidades) ------------------------------------

@dataclass(frozen=True)
class OrderForCrm:
    id: UUID
    customer_id: UUID | None
    order_date: date
    total: Decimal
    status: str
    cancelled: bool


def _order_for_crm(order) -> OrderForCrm:
    return OrderForCrm(id=order.id, customer_id=order.customer_id, order_date=order.order_date, total=order.total,
                       status=order.status, cancelled=order.status == OrderStatus.CANCELLED.value)


def get_order_for_crm(company_id: UUID, order_id: UUID) -> OrderForCrm | None:
    """El pedido de la empresa en cualquier estado (CRM decide si es vinculable), o `None` si es ajeno."""
    order = read_queries.order_by_id(company_id, order_id)
    return _order_for_crm(order) if order else None


def list_orders_for_customer_for_crm(company_id: UUID, customer_id: UUID, limit: int = 50) -> tuple[OrderForCrm, ...]:
    """Pedidos no cancelados del cliente en la empresa, los más recientes primero (máximo `limit`)."""
    orders = read_queries.non_cancelled_orders_of_customer(company_id, customer_id)[:limit]
    return tuple(_order_for_crm(o) for o in orders)
