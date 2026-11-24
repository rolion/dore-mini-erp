"""Único lugar de CRM que conoce a Clientes, Ventas e Inventario, y solo por sus `services.py`."""
from collections.abc import Collection
from uuid import UUID

from modules.crm.application.ports import CommercialSummary, CustomerRef
from modules.customers import services as customer_services
from modules.inventory import services as inventory_services
from modules.sales import services as sales_services
from shared import module_gate


class _CustomerRows:
    def __init__(self, rows):
        self._rows = rows

    def count(self) -> int:
        return self._rows.count()

    def __getitem__(self, index):
        found = self._rows[index]
        if isinstance(index, slice):
            return [CustomerRef(c.id, c.name, c.phone) for c in found]
        return CustomerRef(found.id, found.name, found.phone)


class CustomerDirectoryAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def search_active(self, search: str | None, customer_ids: Collection[UUID] | None):
        return _CustomerRows(customer_services.search_customers_for_crm(self.company_id, search, customer_ids))


class SalesReaderAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def summaries(self, customer_ids: Collection[UUID]) -> dict[UUID, CommercialSummary]:
        found = sales_services.get_customer_commercial_summaries(self.company_id, customer_ids)
        return {
            customer_id: CommercialSummary(s.order_count, s.last_purchase_date, s.outstanding_amount)
            for customer_id, s in found.items()
        }

    def customer_ids_in_warehouse(self, warehouse_id: UUID) -> list[UUID]:
        return sales_services.list_customer_ids_with_orders_in_warehouse(self.company_id, warehouse_id)


class WarehouseDirectoryAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def exists(self, warehouse_id: UUID) -> bool:
        return warehouse_id in inventory_services.get_warehouse_names(self.company_id, [warehouse_id])


class ModuleAvailabilityAdapter:
    """Ventas e Inventario son fuentes opcionales: se consultan una vez por petición."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self._enabled: frozenset[str] | None = None

    def _keys(self) -> frozenset[str]:
        if self._enabled is None:
            self._enabled = module_gate.enabled_keys(self.company_id)
        return self._enabled

    def sales_enabled(self) -> bool:
        return 'sales' in self._keys()

    def inventory_enabled(self) -> bool:
        return 'inventory' in self._keys()
