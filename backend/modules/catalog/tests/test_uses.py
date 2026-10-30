from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.catalog.application.commands import CreateProduct, UpdateProduct
from modules.catalog.application.queries import ListProducts
from modules.catalog.domain.exceptions import ProductValidationError
from modules.catalog.domain.product import CATEGORIES, Product
from modules.catalog.tests.test_application import InMemoryProductRepository


class ProductUsesDomainTests(SimpleTestCase):
    def test_example_products_of_the_business_cases(self):  # AC-03
        queso = Product.create('Queso', category='raw_material', can_buy=True, can_sell=False)
        bolsas = Product.create('Bolsas vacías', category='packaging', can_buy=True, can_sell=False)
        cunape = Product.create('Cuñapé intermedio', category='intermediate', can_buy=False, can_sell=False)
        bolsa_seis = Product.create('Bolsa de seis', '30', category='finished', can_sell=True)
        cuaderno = Product.create('Cuaderno', '12.50', category='merchandise', can_buy=True, can_sell=True)
        products = (queso, bolsas, cunape, bolsa_seis, cuaderno)
        self.assertEqual([p.can_buy for p in products], [True, True, False, False, True])
        self.assertEqual([p.can_sell for p in products], [False, False, False, True, True])
        self.assertIsNone(queso.sale_price)
        self.assertEqual(cuaderno.sale_price, Decimal('12.50'))

    def test_category_does_not_restrict_uses_or_stock(self):  # AC-04, INV-03
        for category in CATEGORIES:
            for can_buy in (True, False):
                for can_sell in (True, False):
                    product = Product.create('x', '1', category=category, can_buy=can_buy, can_sell=can_sell)
                    self.assertEqual((product.category, product.can_buy, product.can_sell),
                                     (category, can_buy, can_sell))

    def test_category_is_required_and_validated(self):  # INV-01, EDGE-01
        for category in (None, '', 'otra', 5):
            with self.assertRaises(ProductValidationError) as ctx:
                Product.create('x', '1', category=category)
            self.assertIn('category', ctx.exception.errors)

    def test_price_required_only_when_it_can_be_sold(self):  # INV-02, AC-05
        with self.assertRaises(ProductValidationError) as ctx:
            Product.create('x', category='finished', can_sell=True)
        self.assertIn('sale_price', ctx.exception.errors)
        self.assertIsNone(Product.create('x', category='finished', can_sell=False).sale_price)

    def test_uses_must_be_booleans(self):  # EDGE-04
        with self.assertRaises(ProductValidationError) as ctx:
            Product.create('x', '1', category='finished', can_buy='si', can_sell=1)
        self.assertEqual(set(ctx.exception.errors), {'can_buy', 'can_sell'})

    def test_price_is_kept_when_it_stops_being_sold(self):  # INV-05
        product = Product.create('x', '10', category='finished')
        product.set_uses(False, False, product.sale_price)
        self.assertEqual(product.sale_price, Decimal('10.00'))

    def test_enabling_sale_without_price_is_rejected(self):  # EDGE-02
        product = Product.create('x', category='raw_material', can_sell=False)
        with self.assertRaises(ProductValidationError) as ctx:
            product.set_uses(False, True, None)
        self.assertIn('sale_price', ctx.exception.errors)
        self.assertFalse(product.can_sell)

    def test_changing_uses_does_not_touch_state_or_stock(self):  # INV-04
        product = Product.create('x', '10', category='finished')
        product.tracks_stock = True
        product.set_uses(True, False, None)
        product.classify('merchandise')
        self.assertTrue(product.active)
        self.assertTrue(product.tracks_stock)

    def test_unclassified_products_need_review(self):  # INV-01
        self.assertTrue(Product(id=uuid4(), name='x', description='', sale_price=Decimal('1')).needs_review)
        self.assertFalse(Product.create('x', '1', category='finished').needs_review)


class ProductUsesUseCaseTests(SimpleTestCase):
    def setUp(self):
        self.repo = InMemoryProductRepository()

    def test_update_uses_and_category_without_losing_other_data(self):  # AC-03, AC-07
        product = CreateProduct(self.repo).execute(name='Cuaderno', sale_price='12', category='finished')
        updated = UpdateProduct(self.repo).execute(product.id, category='merchandise', can_buy=True)
        self.assertEqual((updated.category, updated.can_buy, updated.can_sell, updated.sale_price),
                         ('merchandise', True, True, Decimal('12.00')))

    def test_update_errors_are_collected(self):  # EDGE-01, EDGE-02
        product = CreateProduct(self.repo).execute(name='Queso', category='raw_material', can_sell=False)
        with self.assertRaises(ProductValidationError) as ctx:
            UpdateProduct(self.repo).execute(product.id, category='x', can_sell=True)
        self.assertEqual(set(ctx.exception.errors), {'category', 'sale_price'})
        self.assertFalse(self.repo.get(product.id).can_sell)

    def test_unsellable_product_can_drop_its_price(self):  # AC-05
        product = CreateProduct(self.repo).execute(name='Queso', sale_price='5', category='raw_material',
                                                   can_sell=False)
        updated = UpdateProduct(self.repo).execute(product.id, sale_price=None)
        self.assertIsNone(updated.sale_price)

    def test_list_filters_by_uses_and_category(self):  # AC-08
        create = CreateProduct(self.repo).execute
        create(name='Queso', category='raw_material', can_buy=True, can_sell=False)
        create(name='Cuaderno', sale_price='5', category='merchandise', can_buy=True)
        create(name='Bolsa de seis', sale_price='30', category='finished')
        names = lambda **kw: [p.name for p in ListProducts(self.repo).execute(**kw)]  # noqa: E731
        self.assertEqual(sorted(names(can_buy=True)), ['Cuaderno', 'Queso'])
        self.assertEqual(sorted(names(can_sell=True)), ['Bolsa de seis', 'Cuaderno'])
        self.assertEqual(names(category='raw_material'), ['Queso'])
        self.repo.save(Product(id=uuid4(), name='Viejo', description='', sale_price=Decimal('1')))
        self.assertEqual(names(category='unclassified'), ['Viejo'])
