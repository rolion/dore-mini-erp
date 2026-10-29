from uuid import uuid4

from django.test import TestCase

from modules.catalog.infrastructure.django.models import ProductModel
from modules.purchases.application.ports import ProductInfo
from modules.purchases.infrastructure.adapters import ProductCatalogAdapter


class ProductCatalogAdapterTests(TestCase):
    def test_adapts_the_catalog_facade(self):  # AC-01
        company_id = uuid4()
        product = ProductModel.objects.create(company_id=company_id, name='Harina', sale_price='1.00')
        found = ProductCatalogAdapter(company_id).get_products([product.id, uuid4()])
        self.assertEqual(found, {product.id: ProductInfo(product.id, 'Harina', True, None, False)})
        self.assertEqual(ProductCatalogAdapter(uuid4()).get_products([product.id]), {})
