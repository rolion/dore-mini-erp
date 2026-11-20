"""Puertos de la importación de ventas: el mundo exterior (otros módulos) y el reloj."""
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class Warehouse:
    id: UUID
    name: str
    is_default: bool


@dataclass(frozen=True)
class Capabilities:
    customers: bool
    inventory: bool
    purchases: bool
    accounting: bool
    costing: bool
    warehouses: tuple[Warehouse, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProductRef:
    id: UUID
    name: str
    active: bool
    can_sell: bool
    can_buy: bool
    tracks_stock: bool


@dataclass(frozen=True)
class CustomerRef:
    id: UUID
    name: str
    active: bool


@dataclass(frozen=True)
class SaleLineInput:
    product_id: UUID
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class SaleOutcome:
    order_id: UUID
    code: str
    without_posting: bool


class SalesImportGateway(Protocol):
    """Todo lo que la importación necesita de otros módulos, siempre mediante sus fachadas `services.py`."""

    def capabilities(self) -> Capabilities: ...

    def find_product(self, key: str) -> ProductRef | None: ...

    def find_customer(self, key: str) -> CustomerRef | None: ...

    def find_supplier(self, key: str) -> UUID | None: ...

    def create_product(self, name: str, sale_price: Decimal, tracks_stock: bool, can_buy: bool) -> ProductRef: ...

    def create_customer(self, name: str) -> CustomerRef: ...

    def create_supplier(self, name: str) -> UUID: ...

    def stock_balance(self, warehouse_id: UUID, product_id: UUID) -> Decimal: ...

    def allow_negative_stock(self) -> bool: ...

    def average_cost(self, product_id: UUID) -> Decimal | None: ...

    def is_covered(self, on: date) -> bool: ...

    def receive_purchase(self, supplier_id: UUID, on: date, lines: list[tuple[UUID, int, Decimal]],
                         warehouse_id: UUID | None, post_accounting: bool) -> UUID: ...

    def deliver_sale(self, on: date, sales_channel: str, customer_id: UUID | None, lines: list[SaleLineInput],
                     payment_method: str, warehouse_id: UUID | None, post_accounting: bool,
                     notes: str, discount: Decimal) -> SaleOutcome: ...

    def atomic(self) -> AbstractContextManager[None]: ...

    def reset_cache(self) -> None: ...


class Clock(Protocol):
    def today(self) -> date: ...

    def now(self): ...


@dataclass(frozen=True)
class RunData:
    id: UUID
    filename: str
    status: str
    headers: list[str]
    rows: list[list[str]]
    row_count: int
    mapping: dict
    options: dict
    preview_signature: str
    counts: dict
    idempotency_key: UUID | None
    created_by_name: str
    created_at: object
    finished_at: object


class DuplicateSale(Exception):
    """Otra ejecución ya registró esa venta (la restricción única manda)."""


class ImportRepository(Protocol):
    def create_run(self, filename: str, sha256: str, headers: list[str], rows: list[list[str]],
                   user_id: UUID | None, user_name: str) -> RunData: ...

    def get_run(self, run_id: UUID) -> RunData | None: ...

    def save_preview(self, run_id: UUID, mapping: dict, options: dict, signature: str) -> None: ...

    def claim(self, run_id: UUID, idempotency_key: UUID | None, now) -> None: ...

    def heartbeat(self, run_id: UUID, now) -> None: ...

    def finish(self, run_id: UUID, status: str, counts: dict, now) -> None: ...

    def existing_keys(self, keys: list[str]) -> set[str]: ...

    def record_sale(self, key: str, order_id: UUID, run_id: UUID) -> None: ...

    def add_result(self, run_id: UUID, row_number: int, sale_key: str, status: str, code: str, message: str,
                   order_id: UUID | None, refs: dict) -> None: ...
