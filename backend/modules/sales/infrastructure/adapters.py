"""Adaptadores de los puertos de Sales sobre las fachadas públicas de otros módulos y el reloj de Django.

Es el único lugar de Sales que conoce a Catalog, Customers y Modularity, y solo por sus `services.py`.
"""
import logging
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from modules.catalog import services as catalog_services
from modules.customers import services as customer_services
from modules.inventory import services as inventory_services
from modules.modularity import services as modularity_services
from modules.sales.application.ports import (
    Actor,
    CustomerInfo,
    ProductInfo,
    StockOutputMovement,
    StockOutputRecord,
    StockProductInfo,
    StockWarehouse,
)
from modules.sales.domain.exceptions import (
    InsufficientStockForDelivery,
    OrderRuleViolation,
    OrderValidationError,
    ShortLine,
)
from modules.sales.domain.order import MAX_DISCOUNT_PERCENT
from shared import module_gate

CUSTOMERS_MODULE = 'customers'
INVENTORY_MODULE = 'inventory'

logger = logging.getLogger(__name__)


class ProductCatalogAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get_product_for_sale(self, product_id: UUID) -> ProductInfo | None:
        product = catalog_services.get_product_for_sale(self.company_id, product_id)
        if product is None:
            return None
        return ProductInfo(id=product.id, name=product.name, sale_price=product.sale_price, active=product.active)


class CustomerDirectoryAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Clientes es una integración opcional: con el módulo deshabilitado Ventas funciona sin clientes."""
        if self._available is None:  # una consulta por adaptador (por petición)
            self._available = module_gate.is_enabled(self.company_id, CUSTOMERS_MODULE)
        return self._available

    def get_customer_for_sale(self, customer_id: UUID) -> CustomerInfo | None:
        if not self.is_available():
            return None
        customer = customer_services.get_customer_for_sale(self.company_id, customer_id)
        if customer is None:
            return None
        return CustomerInfo(id=customer.id, name=customer.name, active=customer.active)

    def get_customer_names(self, customer_ids: Iterable[UUID]) -> dict[UUID, str]:
        if not self.is_available():
            return {}
        return customer_services.get_customer_names(self.company_id, customer_ids)


class SalesSettingsAdapter:
    """Configuración de Ventas de la empresa; si no se puede leer, rige el valor inicial (regla previa)."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def max_discount_percent(self) -> Decimal:
        try:
            # Savepoint: un error de BD no debe dejar abortada la transacción de la petición.
            with transaction.atomic():
                return modularity_services.get_sales_settings(self.company_id).max_discount_percent
        except Exception:
            logger.exception('No se pudo leer la configuración de Ventas; se usa el valor inicial.')
            return MAX_DISCOUNT_PERCENT


class StockOutputAdapter:
    """Salidas de inventario al entregar, sobre la fachada de Inventario; es una integración opcional."""

    SOURCE_TYPE = 'sales_order'

    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is None:  # una consulta por adaptador (por petición)
            self._available = module_gate.is_enabled(self.company_id, INVENTORY_MODULE)
        return self._available

    def controlled_products(self, product_ids: Iterable[UUID]) -> dict[UUID, StockProductInfo]:
        found = inventory_services.get_stock_products(self.company_id, product_ids)
        return {pid: StockProductInfo(p.id, p.name, p.unit_abbreviation) for pid, p in found.items()}

    def active_warehouses(self) -> list[StockWarehouse]:
        return [StockWarehouse(w.id, w.name, w.is_default)
                for w in inventory_services.list_active_warehouses(self.company_id)]

    def allow_negative_stock(self) -> bool:
        return inventory_services.allow_negative_stock(self.company_id)

    def balances(self, warehouse_id: UUID, product_ids: Iterable[UUID]) -> dict[UUID, Decimal]:
        return inventory_services.get_balances(self.company_id, warehouse_id, product_ids)

    def register_outputs(self, warehouse_id: UUID, lines: list[tuple[UUID, Decimal]], order_id: UUID,
                         reference: str, actor: Actor) -> None:
        try:
            inventory_services.record_outputs(
                self.company_id, warehouse_id=warehouse_id, lines=lines, source_type=self.SOURCE_TYPE,
                source_id=str(order_id), user_id=actor.user_id, user_name=actor.user_name, reference=reference)
        except inventory_services.InsufficientStock as exc:
            raise self._insufficient(exc) from exc
        except inventory_services.MovementValidationError as exc:
            raise OrderValidationError(self._field_errors(exc.errors)) from exc
        except inventory_services.MovementConflict as exc:
            raise OrderRuleViolation(exc.code, str(exc)) from exc

    def output_for(self, order_id: UUID) -> StockOutputRecord | None:
        if not self.is_available():
            return None
        movements = inventory_services.list_movements_for_source(self.company_id, self.SOURCE_TYPE, str(order_id))
        if not movements:
            return None
        first = movements[0]
        return StockOutputRecord(
            reference=first.reference, warehouse_id=first.warehouse_id, warehouse_name=first.warehouse_name,
            occurred_at=first.occurred_at, user_name=first.user_name,
            movements=[StockOutputMovement(m.id, m.product_id, m.product_name, m.unit_abbreviation, m.quantity)
                       for m in movements])

    @staticmethod
    def _field_errors(errors: dict[str, list[str]]) -> dict[str, list[str]]:
        # Un dato de la salida (almacén) se muestra en su campo; lo demás no es atribuible a la persona.
        return {'warehouse_id' if key == 'warehouse_id' else 'non_field_errors': messages
                for key, messages in errors.items()}

    def _insufficient(self, exc) -> InsufficientStockForDelivery:
        products = inventory_services.get_stock_products(self.company_id, [s.product_id for s in exc.shortages])
        warehouse = next((w for w in self.active_warehouses() if w.id == exc.warehouse_id), None)
        lines = [ShortLine(
            product_id=s.product_id, product_name=products[s.product_id].name if s.product_id in products else '',
            unit=products[s.product_id].unit_abbreviation if s.product_id in products else None,
            requested=s.requested, available=s.available) for s in exc.shortages]
        return InsufficientStockForDelivery(
            str(exc), exc.warehouse_id, warehouse.name if warehouse else '', lines)


class SystemClock:
    """"Hoy" según la zona horaria configurada (`TIME_ZONE`), no la del navegador."""

    def today(self) -> date:
        return timezone.localdate()

    def now(self) -> datetime:
        return timezone.now()
