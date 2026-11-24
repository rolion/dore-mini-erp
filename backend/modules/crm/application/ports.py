"""Puertos de CRM: lo que necesita de otros contextos, expresado con DTO propios."""
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CustomerRef:
    id: UUID
    name: str
    phone: str


@dataclass(frozen=True)
class CommercialSummary:
    order_count: int
    last_purchase_date: date | None
    outstanding_amount: Decimal


class CustomerDirectory(Protocol):
    def search_active(self, search: str | None, customer_ids: Collection[UUID] | None) -> Sequence[CustomerRef]:
        """Clientes activos por nombre e id; admite `count()` y rebanadas."""


class SalesReader(Protocol):
    def summaries(self, customer_ids: Collection[UUID]) -> dict[UUID, CommercialSummary]: ...

    def customer_ids_in_warehouse(self, warehouse_id: UUID) -> list[UUID]: ...


class WarehouseDirectory(Protocol):
    def exists(self, warehouse_id: UUID) -> bool: ...


class ModuleAvailability(Protocol):
    def sales_enabled(self) -> bool: ...

    def inventory_enabled(self) -> bool: ...
