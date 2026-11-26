"""Adaptadores de los puertos de la importación sobre las fachadas `services.py` de otros módulos."""
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from modules.accounting import services as accounting_services
from modules.catalog import services as catalog_services
from modules.costing import services as costing_services
from modules.customers import services as customer_services
from modules.data_import.application.ports import (
    Capabilities,
    CustomerRef,
    ProductRef,
    SaleLineInput,
    SaleOutcome,
    Warehouse,
)
from modules.data_import.domain.normalize import normalize_name
from modules.inventory import services as inventory_services
from modules.purchases import services as purchase_services
from modules.sales import services as sales_services
from shared import module_gate


class SystemClock:
    def today(self):
        return timezone.localdate()

    def now(self):
        return timezone.now()


class SalesImportAdapter:
    """Puerto único de la importación de ventas hacia los demás módulos (solo lectura y escritura por fachadas).

    Mantiene cachés por corrida de productos, clientes y proveedores (clave: nombre normalizado); tras una venta
    fallida se descartan porque pudieron incluir registros revertidos con su transacción.
    """

    def __init__(self, company_id: UUID, user_id: UUID | None, user_name: str):
        self.company_id = company_id
        self.user_id = user_id
        self.user_name = user_name
        self._caps: Capabilities | None = None
        self._products: dict[str, ProductRef] | None = None
        self._customers: dict[str, CustomerRef] | None = None
        self._suppliers: dict[str, UUID] | None = None
        self._costs: dict[UUID, Decimal | None] = {}

    # --- lectura -------------------------------------------------------------------------------------------

    def capabilities(self) -> Capabilities:
        if self._caps is None:
            enabled = module_gate.enabled_keys(self.company_id)
            inventory = 'inventory' in enabled
            warehouses = tuple(Warehouse(w.id, w.name, w.is_default)
                               for w in inventory_services.list_active_warehouses(self.company_id)) if inventory else ()
            self._caps = Capabilities(
                customers='customers' in enabled, inventory=inventory, purchases='purchases' in enabled,
                accounting='accounting' in enabled, costing='costing' in enabled, warehouses=warehouses,
                costing_valued='costing' not in enabled or costing_services.is_valued(self.company_id))
        return self._caps

    def _product_index(self) -> dict[str, ProductRef]:
        if self._products is None:
            index: dict[str, ProductRef] = {}
            for p in catalog_services.list_products_for_import(self.company_id):
                ref = ProductRef(p.id, p.name, p.active, p.can_sell, p.can_buy, p.tracks_stock)
                current = index.get(normalize_name(p.name))
                if current is None or (ref.active and not current.active):
                    index[normalize_name(p.name)] = ref
            self._products = index
        return self._products

    def find_product(self, key: str) -> ProductRef | None:
        return self._product_index().get(key)

    def find_customer(self, key: str) -> CustomerRef | None:
        if self._customers is None:
            index: dict[str, CustomerRef] = {}
            for c in customer_services.list_customers_for_import(self.company_id):
                current = index.get(normalize_name(c.name))
                if current is None or (c.active and not current.active):
                    index[normalize_name(c.name)] = CustomerRef(c.id, c.name, c.active)
            self._customers = index
        return self._customers.get(key)

    def find_supplier(self, key: str) -> UUID | None:
        if self._suppliers is None:
            index: dict[str, tuple[UUID, bool]] = {}
            for s in purchase_services.list_suppliers_for_import(self.company_id):
                current = index.get(normalize_name(s.name))
                if current is None or (s.active and not current[1]):
                    index[normalize_name(s.name)] = (s.id, s.active)
            self._suppliers = {k: v[0] for k, v in index.items() if v[1]}
        return self._suppliers.get(key)

    def stock_balance(self, warehouse_id: UUID, product_id: UUID) -> Decimal:
        balances = inventory_services.get_balances(self.company_id, warehouse_id, [product_id], unlotted=True)
        return balances.get(product_id, Decimal('0'))

    def allow_negative_stock(self) -> bool:
        return inventory_services.allow_negative_stock(self.company_id)

    def average_cost(self, product_id: UUID) -> Decimal | None:
        if not self.capabilities().costing:
            return None
        if product_id not in self._costs:
            self._costs[product_id] = costing_services.get_average_costs(self.company_id, [product_id]).get(product_id)
        return self._costs[product_id]

    def is_covered(self, on) -> bool:
        return self.capabilities().accounting and accounting_services.coverage_status(self.company_id, on).covered

    # --- escritura (por fachadas; reglas del módulo dueño) -------------------------------------------------

    def create_product(self, name: str, sale_price: Decimal, tracks_stock: bool, can_buy: bool,
                       category: str) -> ProductRef:
        created = catalog_services.create_product_for_import(
            self.company_id, name, sale_price, tracks_stock, can_buy, category)
        ref = ProductRef(created.id, created.name, created.active, created.can_sell, created.can_buy,
                         created.tracks_stock)
        self._product_index()[normalize_name(created.name)] = ref
        return ref

    def create_customer(self, name: str) -> CustomerRef:
        created = customer_services.create_customer_for_import(self.company_id, name)
        ref = CustomerRef(created.id, created.name, created.active)
        self.find_customer('')  # asegura el índice
        self._customers[normalize_name(created.name)] = ref
        return ref

    def create_supplier(self, name: str) -> UUID:
        created = purchase_services.create_supplier_for_import(self.company_id, name)
        self.find_supplier('')
        self._suppliers[normalize_name(created.name)] = created.id
        return created.id

    def receive_purchase(self, supplier_id: UUID, on, lines: list[tuple[UUID, int, Decimal]],
                         warehouse_id: UUID | None, post_accounting: bool, payment_method: str) -> UUID:
        purchase = purchase_services.import_received_purchase(
            self.company_id, supplier_id=supplier_id, purchase_date=on,
            lines=[(pid, Decimal(qty), cost) for pid, qty, cost in lines], warehouse_id=warehouse_id,
            user_id=self.user_id, user_name=self.user_name, post_accounting=post_accounting,
            payment_method=payment_method)
        self._costs.clear()
        return purchase.id

    def deliver_sale(self, on, sales_channel: str, customer_id: UUID | None, lines: list[SaleLineInput],
                     payment_method: str, warehouse_id: UUID | None, post_accounting: bool,
                     notes: str, discount: Decimal) -> SaleOutcome:
        sale = sales_services.import_delivered_sale(
            self.company_id, sale_date=on, sales_channel=sales_channel, customer_id=customer_id,
            lines=[sales_services.ImportedSaleLine(l.product_id, l.quantity, l.unit_price) for l in lines],
            payment_method=payment_method, warehouse_id=warehouse_id, user_id=self.user_id,
            user_name=self.user_name, post_accounting=post_accounting, notes=notes,
            discount=discount)
        self._costs.clear()
        return SaleOutcome(sale.order_id, sale.code, sale.without_posting)

    def atomic(self):
        return transaction.atomic()

    def reset_cache(self) -> None:
        self._products = self._customers = self._suppliers = None
        self._costs.clear()
