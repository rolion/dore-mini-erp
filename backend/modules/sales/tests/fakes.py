"""Dobles en memoria de los puertos y del repositorio, para probar casos de uso sin base de datos."""
import copy
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from modules.sales.application.ports import CustomerInfo, ProductInfo
from modules.sales.domain.order import Order
from modules.sales.domain.repositories import OrderFilters, OrderSummary

TODAY = date(2026, 10, 8)
NOW = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)


class InMemoryOrderRepository:
    """Guarda copias profundas para simular la persistencia (lo guardado no se altera por referencia)."""

    def __init__(self):
        self.orders: dict[UUID, Order] = {}
        self.saves = 0

    def get(self, order_id):
        order = self.orders.get(order_id)
        return copy.deepcopy(order) if order else None

    def get_for_update(self, order_id):
        return self.get(order_id)

    def save(self, order):
        self.saves += 1
        self.orders[order.id] = copy.deepcopy(order)
        return copy.deepcopy(order)

    def list(self, filters: OrderFilters):
        return [OrderSummary.from_order(order) for order in self.orders.values()]


class FakeProducts:
    def __init__(self):
        self.items: dict[UUID, ProductInfo] = {}

    def add(self, name='Pack cuñapé', price='35.00', active=True) -> ProductInfo:
        product = ProductInfo(id=uuid4(), name=name, sale_price=Decimal(price), active=active)
        self.items[product.id] = product
        return product

    def get_product_for_sale(self, product_id):
        return self.items.get(product_id)


class FakeCustomers:
    def __init__(self):
        self.items: dict[UUID, CustomerInfo] = {}

    def add(self, name='Ana', active=True) -> CustomerInfo:
        customer = CustomerInfo(id=uuid4(), name=name, active=active)
        self.items[customer.id] = customer
        return customer

    def get_customer_for_sale(self, customer_id):
        return self.items.get(customer_id)

    def get_customer_names(self, customer_ids):
        return {i: self.items[i].name for i in customer_ids if i in self.items}


class FixedClock:
    def __init__(self, today=TODAY, now=NOW):
        self._today = today
        self._now = now

    def today(self):
        return self._today

    def now(self):
        return self._now
