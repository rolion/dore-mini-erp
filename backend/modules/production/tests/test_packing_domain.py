from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from modules.production.domain.packing import Packing, ProductRef, parse_packs
from modules.production.domain.production_order import OrderValidationError

from .test_order_domain import make_order


def ready_order():
    order = make_order()
    order.lot_id = uuid4()
    order.lot_code = 'L-20261127-0001'
    return order


class PackingDomainTests(TestCase):
    def create(self, order, packs=6, pack=None, bag=None):
        return Packing.create(order, request_id=uuid4(), packs=packs, pack=pack or ProductRef(uuid4(), 'Pack x6'),
                              bag=bag or ProductRef(uuid4(), 'Bolsa'), user_id=None, user_name='ana')

    def test_quantities_follow_the_fixed_conversion(self):  # INV-02, AC-01
        order = ready_order()
        packing = self.create(order, packs=6)
        self.assertEqual((packing.packs, packing.bulk_quantity, packing.bags_quantity),
                         (6, Decimal('36'), Decimal('6')))
        self.assertEqual((packing.lot_id, packing.lot_code), (order.lot_id, order.lot_code))

    def test_packs_must_be_a_positive_integer(self):  # AC-07
        for bad in (0, -1, 2.5, 'abc', '', None, True, '2.5', 100000):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_packs(bad)
            with self.subTest(create=bad), self.assertRaises(OrderValidationError) as caught:
                self.create(ready_order(), packs=bad)
            self.assertIn('packs', caught.exception.errors)
        self.assertEqual((parse_packs(3), parse_packs('3')), (3, 3))

    def test_products_must_exist_and_be_distinct_from_each_other_and_from_the_bulk(self):  # INV-03, AC-07
        order = ready_order()
        same = ProductRef(uuid4(), 'Mismo')
        bulk = ProductRef(order.result_product_id, 'Granel')
        for pack, bag, field in ((None, ProductRef(uuid4(), 'B'), 'pack_product_id'),
                                 (ProductRef(uuid4(), 'P'), None, 'bag_product_id'),
                                 (same, same, 'bag_product_id'),
                                 (bulk, ProductRef(uuid4(), 'B'), 'pack_product_id'),
                                 (ProductRef(uuid4(), 'P'), bulk, 'bag_product_id')):
            with self.subTest(field=field, pack=pack, bag=bag), self.assertRaises(OrderValidationError) as caught:
                Packing.create(order, request_id=uuid4(), packs=1, pack=pack, bag=bag, user_id=None, user_name='')
            self.assertIn(field, caught.exception.errors)
