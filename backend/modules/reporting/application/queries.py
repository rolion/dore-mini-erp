from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from modules.reporting.domain.period import Period, resolve_period

from .criteria import SALES_CRITERIA
from .ports import (
    ChannelSales,
    Clock,
    CustomerNames,
    CategoryExpense,
    ExpensesReader,
    PendingOrder,
    ProductSales,
    SalesReader,
    SourceAvailability,
)

LIST_LIMIT = 10
CENTS = Decimal('0.01')


def average_ticket(total: Decimal, orders_count: int) -> Decimal | None:
    """Ventas / pedidos; sin pedidos no hay promedio (evita la división por cero)."""
    if orders_count <= 0:
        return None
    return (total / orders_count).quantize(CENTS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PeriodParams:
    """Parámetros de periodo tal como llegan (sin resolver): `kind` o ambas fechas."""

    kind: str | None = None
    date_from: date | None = None
    date_to: date | None = None


class _PeriodQuery:
    def __init__(self, clock: Clock):
        self.clock = clock

    def _period(self, params: PeriodParams) -> Period:
        return resolve_period(params.kind, params.date_from, params.date_to, self.clock.today())


# --- Resultados -----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SalesReport:
    period: Period
    total: Decimal
    orders_count: int
    average_ticket: Decimal | None
    criteria: str


@dataclass(frozen=True)
class ExpensesReport:
    period: Period
    total: Decimal
    categories: Sequence[CategoryExpense]


@dataclass(frozen=True)
class DashboardSummary:
    """Indicadores del periodo. `None` = fuente deshabilitada (no disponible), nunca cero."""

    period: Period
    sales_enabled: bool
    expenses_enabled: bool
    sales_total: Decimal | None
    orders_count: int | None
    average_ticket: Decimal | None  # None también cuando no hay pedidos
    expenses_total: Decimal | None
    estimated_profit: Decimal | None
    pending_delivery_count: int | None
    pending_collection_count: int | None
    pending_collection_balance: Decimal | None
    sales_criteria: str | None


@dataclass(frozen=True)
class ChannelReport:
    period: Period
    channels: Sequence[ChannelSales]


@dataclass(frozen=True)
class ProductsReport:
    period: Period
    limit: int
    products: Sequence[ProductSales]


@dataclass(frozen=True)
class RankedCustomer:
    customer_id: UUID
    name: str
    orders_count: int
    total: Decimal


@dataclass(frozen=True)
class CustomersReport:
    period: Period
    limit: int
    customers: Sequence[RankedCustomer]


@dataclass(frozen=True)
class PendingRow:
    order: PendingOrder
    customer_name: str | None  # None cuando el módulo Clientes está deshabilitado


@dataclass(frozen=True)
class PendingList:
    count: int
    balance_total: Decimal
    rows: Sequence[PendingRow]


@dataclass(frozen=True)
class PendingReport:
    delivery: PendingList
    collection: PendingList


# --- Casos de uso ---------------------------------------------------------------------------------------------


class GetSalesReport(_PeriodQuery):
    def __init__(self, sales: SalesReader, clock: Clock):
        super().__init__(clock)
        self.sales = sales

    def execute(self, params: PeriodParams) -> SalesReport:
        period = self._period(params)
        totals = self.sales.totals(period.date_from, period.date_to)
        return SalesReport(period=period, total=totals.total, orders_count=totals.orders_count,
                           average_ticket=average_ticket(totals.total, totals.orders_count),
                           criteria=SALES_CRITERIA)


class GetExpenseReport(_PeriodQuery):
    def __init__(self, expenses: ExpensesReader, clock: Clock):
        super().__init__(clock)
        self.expenses = expenses

    def execute(self, params: PeriodParams) -> ExpensesReport:
        period = self._period(params)
        report = self.expenses.report(period.date_from, period.date_to)
        return ExpensesReport(period=period, total=report.total, categories=report.categories)


class GetDashboardSummary(_PeriodQuery):
    """Ganancia estimada = ventas − gastos vigentes del periodo (puede ser negativa); los cobros no intervienen.

    Solo se consultan las fuentes habilitadas; si falta Ventas o Gastos la ganancia no se calcula.
    """

    def __init__(self, sales: SalesReader, expenses: ExpensesReader, sources: SourceAvailability, clock: Clock):
        super().__init__(clock)
        self.sales = sales
        self.expenses = expenses
        self.sources = sources

    def execute(self, params: PeriodParams) -> DashboardSummary:
        period = self._period(params)
        sales_on, expenses_on = self.sources.sales_enabled(), self.sources.expenses_enabled()
        sales_total = orders_count = ticket = None
        delivery_count = collection_count = collection_balance = criteria = None
        if sales_on:
            totals = self.sales.totals(period.date_from, period.date_to)
            sales_total, orders_count = totals.total, totals.orders_count
            ticket = average_ticket(totals.total, totals.orders_count)
            delivery = self.sales.pending_delivery(0)
            collection = self.sales.pending_collection(0)
            delivery_count, collection_count = delivery.count, collection.count
            collection_balance = collection.balance_total
            criteria = SALES_CRITERIA
        expenses_total = self.expenses.report(period.date_from, period.date_to).total if expenses_on else None
        profit = sales_total - expenses_total if sales_on and expenses_on else None
        return DashboardSummary(
            period=period, sales_enabled=sales_on, expenses_enabled=expenses_on,
            sales_total=sales_total, orders_count=orders_count, average_ticket=ticket,
            expenses_total=expenses_total, estimated_profit=profit,
            pending_delivery_count=delivery_count, pending_collection_count=collection_count,
            pending_collection_balance=collection_balance, sales_criteria=criteria,
        )


class GetSalesByChannel(_PeriodQuery):
    def __init__(self, sales: SalesReader, clock: Clock):
        super().__init__(clock)
        self.sales = sales

    def execute(self, params: PeriodParams) -> ChannelReport:
        period = self._period(params)
        return ChannelReport(period=period, channels=self.sales.by_channel(period.date_from, period.date_to))


class GetTopProducts(_PeriodQuery):
    def __init__(self, sales: SalesReader, clock: Clock):
        super().__init__(clock)
        self.sales = sales

    def execute(self, params: PeriodParams, limit: int = LIST_LIMIT) -> ProductsReport:
        period = self._period(params)
        products = self.sales.top_products(period.date_from, period.date_to, limit)
        return ProductsReport(period=period, limit=limit, products=products)


class GetTopCustomers(_PeriodQuery):
    def __init__(self, sales: SalesReader, customers: CustomerNames, clock: Clock):
        super().__init__(clock)
        self.sales = sales
        self.customers = customers

    def execute(self, params: PeriodParams, limit: int = LIST_LIMIT) -> CustomersReport:
        period = self._period(params)
        rows = self.sales.top_customers(period.date_from, period.date_to, limit)
        names = self.customers.get_customer_names([row.customer_id for row in rows])
        ranked = [RankedCustomer(customer_id=row.customer_id, name=names.get(row.customer_id, ''),
                                 orders_count=row.orders_count, total=row.total) for row in rows]
        return CustomersReport(period=period, limit=limit, customers=ranked)


class GetPendingOrders:
    """Estado actual de todos los pedidos: no recibe periodo."""

    def __init__(self, sales: SalesReader, customers: CustomerNames):
        self.sales = sales
        self.customers = customers

    def execute(self, limit: int = LIST_LIMIT) -> PendingReport:
        delivery = self.sales.pending_delivery(limit)
        collection = self.sales.pending_collection(limit)
        ids = {o.customer_id for o in (*delivery.rows, *collection.rows) if o.customer_id is not None}
        names = self.customers.get_customer_names(ids)
        available = self.customers.is_available()

        def build(pending) -> PendingList:
            rows = [PendingRow(order=o, customer_name=names.get(o.customer_id, '') if available else None)
                    for o in pending.rows]
            return PendingList(count=pending.count, balance_total=pending.balance_total, rows=rows)

        return PendingReport(delivery=build(delivery), collection=build(collection))
