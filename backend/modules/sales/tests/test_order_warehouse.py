"""INV-07: el almacén del pedido solo cambia por el método del agregado y mientras el pedido admite cambios."""
from datetime import date
from uuid import uuid4

from django.test import SimpleTestCase

from modules.sales.domain.enums import OrderStatus
from modules.sales.domain.exceptions import OrderRuleViolation
from modules.sales.domain.order import Order


class AssignWarehouseTests(SimpleTestCase):
    def order(self) -> Order:
        return Order.create('WHATSAPP', date(2026, 10, 1))

    def test_a_new_order_has_no_warehouse(self):
        self.assertIsNone(self.order().warehouse_id)

    def test_assigns_and_clears_the_warehouse_while_editable(self):
        order, warehouse_id = self.order(), uuid4()
        order.assign_warehouse(warehouse_id)
        self.assertEqual(order.warehouse_id, warehouse_id)
        order.assign_warehouse(None)
        self.assertIsNone(order.warehouse_id)

    def test_a_closed_order_rejects_the_change(self):
        for status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            order = self.order()
            order.status = status
            with self.assertRaises(OrderRuleViolation) as raised:
                order.assign_warehouse(uuid4())
            self.assertEqual(raised.exception.code, 'order_not_editable')
