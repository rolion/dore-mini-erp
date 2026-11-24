from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from .ports import CommercialSummary, CustomerDirectory, ModuleAvailability, SalesReader, WarehouseDirectory

# Moneda del producto (constante única hoy; no hay moneda por empresa).
CURRENCY = 'BOB'
ZERO = Decimal('0.00')
EMPTY_SUMMARY = CommercialSummary(order_count=0, last_purchase_date=None, outstanding_amount=ZERO)


class WarehouseFilterUnavailable(Exception):
    """El filtro de sucursal exige Ventas e Inventario habilitados."""


class WarehouseNotFound(Exception):
    """El almacén no existe en la empresa."""


@dataclass(frozen=True)
class CrmCustomerRow:
    customer_id: UUID
    display_name: str
    phone: str
    last_purchase_at: date | None
    order_count: int
    outstanding_amount: Decimal
    currency: str


class CrmCustomerRows:
    """Filas paginables: los agregados de Ventas se piden solo para los clientes de la página pedida."""

    def __init__(self, customers: Sequence, sales: SalesReader | None):
        self._customers = customers
        self._sales = sales

    def count(self) -> int:
        return self._customers.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if not isinstance(index, slice):
            return self[index:index + 1][0]
        page = self._customers[index]
        summaries = self._sales.summaries([c.id for c in page]) if self._sales else {}
        return [self._row(c, summaries.get(c.id, EMPTY_SUMMARY)) for c in page]

    @staticmethod
    def _row(customer, summary: CommercialSummary) -> CrmCustomerRow:
        return CrmCustomerRow(
            customer_id=customer.id, display_name=customer.name, phone=customer.phone,
            last_purchase_at=summary.last_purchase_date, order_count=summary.order_count,
            outstanding_amount=summary.outstanding_amount, currency=CURRENCY)


@dataclass(frozen=True)
class CrmCustomerListing:
    rows: CrmCustomerRows
    sales_enabled: bool
    warehouse_filter_enabled: bool


class ListCrmCustomers:
    def __init__(self, customers: CustomerDirectory, sales: SalesReader, warehouses: WarehouseDirectory,
                 availability: ModuleAvailability):
        self.customers = customers
        self.sales = sales
        self.warehouses = warehouses
        self.availability = availability

    def execute(self, search: str | None = None, warehouse_id: UUID | None = None) -> CrmCustomerListing:
        sales_enabled = self.availability.sales_enabled()
        filter_enabled = sales_enabled and self.availability.inventory_enabled()
        customer_ids = None
        if warehouse_id is not None:
            if not filter_enabled:
                raise WarehouseFilterUnavailable()
            if not self.warehouses.exists(warehouse_id):
                raise WarehouseNotFound()
            customer_ids = self.sales.customer_ids_in_warehouse(warehouse_id)
        customers = self.customers.search_active(search, customer_ids)
        rows = CrmCustomerRows(customers, self.sales if sales_enabled else None)
        return CrmCustomerListing(rows=rows, sales_enabled=sales_enabled, warehouse_filter_enabled=filter_enabled)
