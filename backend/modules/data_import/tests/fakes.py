from contextlib import nullcontext
from datetime import date
from decimal import Decimal
from uuid import uuid4

from modules.data_import.application.ports import (
    Capabilities,
    CustomerRef,
    DuplicateSale,
    ProductRef,
    RunData,
    SaleOutcome,
    Warehouse,
)
from modules.data_import.domain.errors import ImportRuleViolation
from shared.import_errors import ImportRejected

WAREHOUSE = Warehouse(uuid4(), 'Principal', True)


class FakeClock:
    def today(self):
        return date(2026, 11, 19)

    def now(self):
        return None


class FakeRepository:
    def __init__(self, headers, rows):
        self.run = RunData(uuid4(), 'f.csv', 'UPLOADED', headers, rows, len(rows), {}, {}, '', {}, None, 'u',
                           None, None)
        self.keys: set[str] = set()
        self.results: list[tuple] = []
        self.running = False

    def get_run(self, run_id):
        return self.run if run_id == self.run.id else None

    def save_preview(self, run_id, mapping, options, signature):
        self.run = RunData(**{**self.run.__dict__, 'mapping': mapping, 'options': options,
                              'preview_signature': signature, 'status': 'PREVIEWED'})

    def claim(self, run_id, key, now):
        if self.running:
            raise ImportRuleViolation('import_running', 'en curso')
        self.run = RunData(**{**self.run.__dict__, 'status': 'RUNNING'})

    def heartbeat(self, run_id, now):
        pass

    def finish(self, run_id, status, counts, now):
        self.run = RunData(**{**self.run.__dict__, 'status': status, 'counts': counts})

    def existing_keys(self, keys):
        return self.keys & set(keys)

    def record_sale(self, key, order_id, run_id):
        if key in self.keys:
            raise DuplicateSale(key)
        self.keys.add(key)

    def add_result(self, run_id, row_number, sale_key, status, code, message, order_id, refs):
        self.results.append((row_number, sale_key, status, code, message, order_id, refs))
        if status in ('CREATED', 'CREATED_WITHOUT_POSTING') and sale_key not in self.keys:
            self.keys.add(sale_key)


class FakeGateway:
    def __init__(self, products=(), customers=(), stock=None, covered=True, costs=None, **caps):
        base = dict(customers=True, inventory=True, purchases=True, accounting=True, costing=True,
                    warehouses=(WAREHOUSE,))
        base.update(caps)
        self.caps = Capabilities(**base)
        self.products = {n: ProductRef(uuid4(), n, True, True, True, tracks) for n, tracks in products}
        self.customers = {n: CustomerRef(uuid4(), n, True) for n in customers}
        self.stock = stock if stock is not None else {}
        self.covered = covered
        self.costs = costs or {}
        self.created_products: list[str] = []
        self.purchases: list[tuple] = []
        self.sales: list[dict] = []
        self.fail_sale_with: ImportRejected | None = None

    def capabilities(self):
        return self.caps

    def find_product(self, key):
        return self.products.get(key)

    def find_customer(self, key):
        return self.customers.get(key)

    def find_supplier(self, key):
        return None

    def create_product(self, name, sale_price, tracks_stock, can_buy, category):
        ref = ProductRef(uuid4(), name, True, True, can_buy, tracks_stock)
        self.products[name.lower()] = ref
        self.created_products.append(name)
        return ref

    def create_customer(self, name):
        ref = CustomerRef(uuid4(), name, True)
        self.customers[name.lower()] = ref
        return ref

    def create_supplier(self, name):
        return uuid4()

    def stock_balance(self, warehouse_id, product_id):
        return Decimal(self.stock.get(product_id, 0))

    def allow_negative_stock(self):
        return False

    def average_cost(self, product_id):
        return self.costs.get(product_id)

    def is_covered(self, on):
        return self.covered

    def receive_purchase(self, supplier_id, on, lines, warehouse_id, post_accounting):
        self.purchases.append((supplier_id, on, lines, post_accounting))
        for pid, qty, _ in lines:
            self.stock[pid] = self.stock.get(pid, 0) + qty
        return uuid4()

    def deliver_sale(self, on, sales_channel, customer_id, lines, payment_method, warehouse_id, post_accounting,
                     notes, discount):
        if self.fail_sale_with is not None:
            raise self.fail_sale_with
        for line in lines:
            if line.product_id in self.stock:
                self.stock[line.product_id] -= line.quantity
        self.sales.append({'on': on, 'method': payment_method, 'post': post_accounting, 'lines': lines})
        return SaleOutcome(uuid4(), 'P-1', not self.covered)

    def atomic(self):
        return nullcontext()

    def reset_cache(self):
        pass
