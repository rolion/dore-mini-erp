from dataclasses import FrozenInstanceError
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

from modules.catalog.infrastructure.django.models import ProductModel
from modules.catalog.services import ProductForSale, get_product_for_sale


class GetProductForSaleTests(TestCase):
    def test_returns_current_name_price_and_state(self):  # AC-21
        product = ProductModel.objects.create(name='Pack cuñapé', description='', sale_price=Decimal('35.00'))
        self.assertEqual(
            get_product_for_sale(product.id),
            ProductForSale(id=product.id, name='Pack cuñapé', sale_price=Decimal('35.00'), active=True),
        )

    def test_inactive_products_are_returned_with_their_state(self):  # AC-21
        product = ProductModel.objects.create(name='Viejo', description='', sale_price=Decimal('1.00'), active=False)
        self.assertFalse(get_product_for_sale(product.id).active)

    def test_unknown_product_returns_none(self):  # AC-21
        self.assertIsNone(get_product_for_sale(uuid4()))

    def test_dto_is_immutable(self):  # AC-21
        product = ProductModel.objects.create(name='A', description='', sale_price=Decimal('1.00'))
        with self.assertRaises(FrozenInstanceError):
            get_product_for_sale(product.id).name = 'B'
