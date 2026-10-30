"""PB-INT-002: `DeliverOrder` y vista previa con un doble en memoria de Inventario (sin base de datos)."""
from decimal import Decimal
from uuid import uuid4

from modules.sales.application.commands import DeliverOrder, MarkOrderReady, StartOrderPreparation
from modules.sales.application.delivery import PreviewOrderDelivery
from modules.sales.application.ports import Actor, StockProductInfo, StockWarehouse
from modules.sales.domain.enums import OrderStatus
from modules.sales.domain.exceptions import OrderRuleViolation, OrderValidationError

from .fakes import FixedClock
from .test_application import ApplicationTestCase


class FakeStock:
    def __init__(self, available=True):
        self.available = available
        self.products: dict = {}
        self.warehouses = [StockWarehouse(uuid4(), 'Central', True)]
        self.negative = False
        self.balance: dict = {}
        self.registered: list = []
        self.fail_with: Exception | None = None

    def control(self, product):
        self.products[product.id] = StockProductInfo(product.id, product.name, 'u')

    def is_available(self):
        return self.available

    def controlled_products(self, product_ids):
        return {pid: self.products[pid] for pid in product_ids if pid in self.products}

    def active_warehouses(self):
        return list(self.warehouses)

    def allow_negative_stock(self):
        return self.negative

    def balances(self, warehouse_id, product_ids):
        return {pid: self.balance.get(pid, Decimal('0')) for pid in product_ids}

    def register_outputs(self, warehouse_id, lines, order_id, reference, actor):
        if self.fail_with:
            raise self.fail_with
        self.registered.append((warehouse_id, lines, order_id, reference, actor))

    def output_for(self, order_id):
        return None


class DeliveryApplicationTests(ApplicationTestCase):
    def setUp(self):
        super().setUp()
        self.stock = FakeStock()

    def ready(self, *products_and_quantities):
        order = self.create()
        for product, quantity in products_and_quantities:
            order = self.add_item(order, product, quantity)
        StartOrderPreparation(self.repository).execute(order.id)
        return MarkOrderReady(self.repository).execute(order.id)

    def use_case(self):
        return DeliverOrder(self.repository, FixedClock(), self.stock)

    def test_registers_one_exit_per_controlled_product_with_the_order_reference(self):  # AC-01, AC-06, AC-10
        bags, service = self.products.add('Bolsas'), self.products.add('Servicio')
        self.stock.control(bags)
        order = self.ready((bags, 4), (service, 2))
        actor = Actor(uuid4(), 'ana')
        warehouse = self.stock.warehouses[0].id
        delivered = self.use_case().execute(order.id, warehouse_id=warehouse, actor=actor)
        self.assertEqual(delivered.status, OrderStatus.DELIVERED)
        self.assertEqual(self.stock.registered, [(warehouse, [(bags.id, Decimal('4'))], order.id, order.code, actor)])

    def test_no_controlled_items_needs_no_warehouse(self):  # AC-06
        order = self.ready((self.products.add('Servicio'), 2))
        delivered = self.use_case().execute(order.id)
        self.assertEqual((delivered.status, self.stock.registered), (OrderStatus.DELIVERED, []))

    def test_disabled_inventory_or_missing_port_delivers_as_before(self):  # AC-08
        bags = self.products.add('Bolsas')
        self.stock.control(bags)
        order = self.ready((bags, 4))
        self.stock.available = False
        self.assertEqual(self.use_case().execute(order.id).status, OrderStatus.DELIVERED)
        self.assertEqual(self.stock.registered, [])
        other = self.ready((bags, 1))
        self.assertEqual(DeliverOrder(self.repository, FixedClock()).execute(other.id).status, OrderStatus.DELIVERED)

    def test_warehouse_is_required_for_controlled_items(self):  # AC-07
        bags = self.products.add('Bolsas')
        self.stock.control(bags)
        order = self.ready((bags, 4))
        with self.assertRaises(OrderValidationError) as ctx:
            self.use_case().execute(order.id)
        self.assertIn('warehouse_id', ctx.exception.errors)
        self.assertEqual(self.repository.orders[order.id].status, OrderStatus.READY)

    def test_without_an_active_warehouse_it_is_a_rule_violation(self):  # AC-07
        bags = self.products.add('Bolsas')
        self.stock.control(bags)
        self.stock.warehouses = []
        order = self.ready((bags, 4))
        with self.assertRaises(OrderRuleViolation) as ctx:
            self.use_case().execute(order.id, warehouse_id=uuid4())
        self.assertEqual(ctx.exception.code, 'no_active_warehouse')

    def test_a_failing_exit_leaves_the_order_unsaved(self):  # AC-05, INV-02
        bags = self.products.add('Bolsas')
        self.stock.control(bags)
        order = self.ready((bags, 4))
        saves = self.repository.saves
        self.stock.fail_with = OrderRuleViolation('insufficient_stock', 'sin saldo')
        with self.assertRaises(OrderRuleViolation):
            self.use_case().execute(order.id, warehouse_id=self.stock.warehouses[0].id)
        self.assertEqual((self.repository.saves, self.repository.orders[order.id].status),
                         (saves, OrderStatus.READY))

    def test_invalid_transition_never_reaches_inventory(self):  # AC-04
        bags = self.products.add('Bolsas')
        self.stock.control(bags)
        order = self.ready((bags, 4))
        warehouse = self.stock.warehouses[0].id
        self.use_case().execute(order.id, warehouse_id=warehouse)
        with self.assertRaises(OrderRuleViolation) as ctx:
            self.use_case().execute(order.id, warehouse_id=warehouse)
        self.assertEqual((ctx.exception.code, len(self.stock.registered)), ('invalid_transition', 1))


class PreviewApplicationTests(DeliveryApplicationTests):
    def preview(self, order, warehouse_id=None):
        return PreviewOrderDelivery(self.repository, self.stock).execute(order.id, warehouse_id)

    def test_projected_balance_and_selection(self):  # AC-11
        bags = self.products.add('Bolsas')
        self.stock.control(bags)
        self.stock.balance[bags.id] = Decimal('5')
        preview = self.preview(self.ready((bags, 4)))
        line = preview.lines[0]
        self.assertEqual((preview.warehouse_id, line.available, line.projected, line.insufficient),
                         (self.stock.warehouses[0].id, Decimal('5'), Decimal('1'), False))

    def test_with_two_warehouses_the_default_is_suggested_and_a_foreign_one_is_rejected(self):  # AC-11, AC-07
        bags = self.products.add('Bolsas')
        self.stock.control(bags)
        second = StockWarehouse(uuid4(), 'Zona', False)
        self.stock.warehouses.append(second)
        order = self.ready((bags, 1))
        self.assertEqual(self.preview(order).warehouse_id, self.stock.warehouses[0].id)
        self.assertEqual(self.preview(order, second.id).warehouse_id, second.id)
        with self.assertRaises(OrderValidationError):
            self.preview(order, uuid4())

    def test_no_default_and_several_warehouses_selects_nothing(self):  # AC-11
        bags = self.products.add('Bolsas')
        self.stock.control(bags)
        self.stock.warehouses = [StockWarehouse(uuid4(), 'A', False), StockWarehouse(uuid4(), 'B', False)]
        preview = self.preview(self.ready((bags, 1)))
        self.assertEqual((preview.warehouse_id, preview.lines[0].available), (None, None))
