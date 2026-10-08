from decimal import Decimal

from django.test import SimpleTestCase

from modules.catalog.domain.exceptions import ProductValidationError
from modules.catalog.domain.product import Product


class ProductCreateTests(SimpleTestCase):
    def test_create_valid_is_active_by_default(self):  # INV-03
        product = Product.create(name='  Pack 10 cuñapés  ', sale_price='35', description=' tradicional ')
        self.assertEqual(product.name, 'Pack 10 cuñapés')  # EDGE-01: recortado
        self.assertEqual(product.description, 'tradicional')
        self.assertEqual(product.sale_price, Decimal('35.00'))
        self.assertTrue(product.active)

    def test_name_is_required(self):  # INV-01
        for name in (None, '', '   ', 5):
            with self.assertRaises(ProductValidationError) as ctx:
                Product.create(name=name, sale_price='1')
            self.assertIn('name', ctx.exception.errors)

    def test_name_max_length(self):  # INV-01 / EDGE-01
        Product.create(name='a' * 150, sale_price='1')
        with self.assertRaises(ProductValidationError) as ctx:
            Product.create(name='a' * 151, sale_price='1')
        self.assertIn('name', ctx.exception.errors)

    def test_price_zero_is_valid(self):  # INV-02
        self.assertEqual(Product.create(name='x', sale_price='0').sale_price, Decimal('0.00'))
        self.assertEqual(Product.create(name='x', sale_price=Decimal('0.00')).sale_price, Decimal('0.00'))

    def test_price_formats_accepted(self):  # EDGE-02
        for raw, expected in (('35', '35.00'), ('35.5', '35.50'), ('35.50', '35.50'), (10, '10.00'),
                              ('9999999999.99', '9999999999.99')):
            self.assertEqual(Product.create(name='x', sale_price=raw).sale_price, Decimal(expected))

    def test_price_invalid_rejected(self):  # INV-02 / EDGE-02
        for raw in (None, '', 'abc', '-1', '-0.01', '35.555', '10000000000.00', 35.5, True,
                    'NaN', 'Infinity'):
            with self.assertRaises(ProductValidationError, msg=repr(raw)) as ctx:
                Product.create(name='x', sale_price=raw)
            self.assertIn('sale_price', ctx.exception.errors)

    def test_errors_are_collected_per_field(self):
        with self.assertRaises(ProductValidationError) as ctx:
            Product.create(name='', sale_price='-1')
        self.assertEqual(set(ctx.exception.errors), {'name', 'sale_price'})


class ProductBehaviorTests(SimpleTestCase):
    def setUp(self):
        self.product = Product.create(name='Cuñapé', sale_price='10')

    def test_rename_describe_and_change_price(self):
        self.product.rename(' Cuñapé grande ')
        self.product.describe(None)
        self.product.change_price('12.5')
        self.assertEqual(
            (self.product.name, self.product.description, self.product.sale_price),
            ('Cuñapé grande', '', Decimal('12.50')),
        )

    def test_invalid_changes_keep_previous_values(self):
        with self.assertRaises(ProductValidationError):
            self.product.rename('')
        with self.assertRaises(ProductValidationError):
            self.product.change_price('-5')
        self.assertEqual((self.product.name, self.product.sale_price), ('Cuñapé', Decimal('10.00')))

    def test_activate_and_deactivate_are_idempotent(self):  # INV-04
        self.product.deactivate()
        self.product.deactivate()
        self.assertFalse(self.product.active)
        self.product.activate()
        self.product.activate()
        self.assertTrue(self.product.active)
