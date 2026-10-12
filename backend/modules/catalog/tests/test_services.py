from dataclasses import FrozenInstanceError
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

from modules.catalog.infrastructure.django.models import ProductModel
from modules.catalog.services import ProductForSale, get_product_for_sale


COMPANY_ID = uuid4()


class GetProductForSaleTests(TestCase):
    def test_returns_current_name_price_and_state(self):  # AC-21
        product = ProductModel.objects.create(company_id=COMPANY_ID, name='Pack cuñapé', description='', sale_price=Decimal('35.00'))
        self.assertEqual(
            get_product_for_sale(COMPANY_ID, product.id),
            ProductForSale(id=product.id, name='Pack cuñapé', sale_price=Decimal('35.00'), active=True),
        )

    def test_inactive_products_are_returned_with_their_state(self):  # AC-21
        product = ProductModel.objects.create(company_id=COMPANY_ID, name='Viejo', description='', sale_price=Decimal('1.00'), active=False)
        self.assertFalse(get_product_for_sale(COMPANY_ID, product.id).active)

    def test_unknown_product_returns_none(self):  # AC-21
        self.assertIsNone(get_product_for_sale(COMPANY_ID, uuid4()))

    def test_dto_is_immutable(self):  # AC-21
        product = ProductModel.objects.create(company_id=COMPANY_ID, name='A', description='', sale_price=Decimal('1.00'))
        with self.assertRaises(FrozenInstanceError):
            get_product_for_sale(COMPANY_ID, product.id).name = 'B'

    def test_product_of_another_company_is_not_visible(self):  # AC-06
        product = ProductModel.objects.create(company_id=uuid4(), name='Ajeno', description='', sale_price=Decimal('1.00'))
        self.assertIsNone(get_product_for_sale(COMPANY_ID, product.id))
