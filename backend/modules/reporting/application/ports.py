"""Puertos que Reporting necesita del exterior: lectores de Sales y Expenses, nombres de clientes y el reloj.

Las implementaciones viven en `infrastructure/adapters.py` y solo llaman a las fachadas `services.py`.
"""
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID


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
    amount: Decimal


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
    rows: Sequence[PendingOrder]


@dataclass(frozen=True)
class CategoryExpense:
    category_id: UUID
    name: str
    active: bool
    total: Decimal


@dataclass(frozen=True)
class ExpenseTotals:
    total: Decimal
    categories: Sequence[CategoryExpense]


class SalesReader(Protocol):
    def totals(self, date_from: date, date_to: date) -> SalesTotals: ...

    def by_channel(self, date_from: date, date_to: date) -> Sequence[ChannelSales]: ...

    def top_products(self, date_from: date, date_to: date, limit: int) -> Sequence[ProductSales]: ...

    def top_customers(self, date_from: date, date_to: date, limit: int) -> Sequence[CustomerSales]: ...

    def pending_delivery(self, limit: int) -> PendingOrders: ...

    def pending_collection(self, limit: int) -> PendingOrders: ...


class ExpensesReader(Protocol):
    def report(self, date_from: date, date_to: date) -> ExpenseTotals: ...


class CustomerNames(Protocol):
    def get_customer_names(self, customer_ids: Iterable[UUID]) -> dict[UUID, str]: ...


class Clock(Protocol):
    def today(self) -> date: ...
