from decimal import Decimal
from uuid import uuid4

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.catalog.infrastructure.django.models import ProductModel
from modules.catalog.services import ProductForPurchase, get_product_for_purchase, get_product_for_sale

LIST_URL = '/api/products/'


class ProductUsesApiTests(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))

    def post(self, body, expected=201):
        response = self.client.post(LIST_URL, body, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def test_business_examples_can_be_created(self):  # AC-03
        queso = self.post({'name': 'Queso', 'category': 'raw_material', 'can_buy': True, 'can_sell': False})
        self.post({'name': 'Bolsas vacías', 'category': 'packaging', 'can_buy': True, 'can_sell': False})
        cunape = self.post({'name': 'Cuñapé intermedio', 'category': 'intermediate', 'can_sell': False,
                            'tracks_stock': False})
        self.post({'name': 'Bolsa de seis', 'category': 'finished', 'sale_price': '30'})
        cuaderno = self.post({'name': 'Cuaderno', 'category': 'merchandise', 'can_buy': True, 'can_sell': True,
                              'sale_price': '12.50'})
        self.assertEqual((queso['can_buy'], queso['can_sell'], queso['sale_price']), (True, False, None))
        self.assertEqual((cunape['can_buy'], cunape['can_sell']), (False, False))
        self.assertEqual((cuaderno['can_buy'], cuaderno['can_sell'], cuaderno['sale_price']), (True, True, '12.50'))
        self.assertFalse(cuaderno['needs_review'])

    def test_defaults_when_uses_are_omitted(self):  # API-02
        body = self.post({'name': 'Pack', 'category': 'finished', 'sale_price': '10'})
        self.assertEqual((body['can_buy'], body['can_sell']), (False, True))

    def test_category_is_required_and_validated(self):  # EDGE-01
        for payload in ({'name': 'x', 'sale_price': '1'}, {'name': 'x', 'sale_price': '1', 'category': None},
                        {'name': 'x', 'sale_price': '1', 'category': 'otra'}):
            self.assertIn('category', self.post(payload, 400))
        self.assertEqual(ProductModel.objects.count(), 0)

    def test_price_required_only_when_sellable(self):  # AC-05
        self.assertIn('sale_price', self.post({'name': 'x', 'category': 'finished'}, 400))
        self.post({'name': 'Insumo', 'category': 'raw_material', 'can_sell': False})

    def test_patch_uses_and_category_keeps_stock_unit_and_price(self):  # AC-04, AC-07, INV-04
        unit = self.client.post('/api/units/', {'name': 'Unidad', 'abbreviation': 'u'}, format='json').json()
        product = self.post({'name': 'Cuaderno', 'category': 'finished', 'sale_price': '5',
                             'tracks_stock': True, 'base_unit_id': unit['id']})
        response = self.client.patch(f'{LIST_URL}{product["id"]}/', {'category': 'merchandise', 'can_buy': True,
                                                                    'can_sell': False}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['category'], body['can_buy'], body['can_sell']), ('merchandise', True, False))
        self.assertEqual((body['sale_price'], body['tracks_stock'], body['base_unit_id'], body['active']),
                         ('5.00', True, unit['id'], True))

    def test_patch_enabling_sale_without_price_is_rejected(self):  # EDGE-02
        product = self.post({'name': 'Queso', 'category': 'raw_material', 'can_sell': False})
        response = self.client.patch(f'{LIST_URL}{product["id"]}/', {'can_sell': True}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('sale_price', response.json())
        response = self.client.patch(f'{LIST_URL}{product["id"]}/', {'can_sell': True, 'sale_price': '9'},
                                     format='json')
        self.assertEqual(response.status_code, 200, response.content)

    def test_patch_cannot_clear_the_category(self):  # INV-01
        product = self.post({'name': 'x', 'category': 'finished', 'sale_price': '1'})
        response = self.client.patch(f'{LIST_URL}{product["id"]}/', {'category': None}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_legacy_product_is_unclassified_and_editable_without_category(self):  # AC-06, EDGE-03
        legacy = ProductModel.objects.create(company_id=self.company.id, name='Viejo', description='',
                                             sale_price=Decimal('4.00'))
        body = self.client.get(f'{LIST_URL}{legacy.id}/').json()
        self.assertEqual((body['category'], body['can_buy'], body['can_sell'], body['needs_review']),
                         (None, False, True, True))
        response = self.client.patch(f'{LIST_URL}{legacy.id}/', {'name': 'Viejo 2'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)

    def test_list_filters(self):  # AC-08
        self.post({'name': 'Queso', 'category': 'raw_material', 'can_buy': True, 'can_sell': False})
        self.post({'name': 'Cuaderno', 'category': 'merchandise', 'can_buy': True, 'sale_price': '5'})
        self.post({'name': 'Bolsa', 'category': 'finished', 'sale_price': '30'})
        ProductModel.objects.create(company_id=self.company.id, name='Viejo', description='',
                                    sale_price=Decimal('1.00'), active=False)

        def names(**params):
            return [p['name'] for p in self.client.get(LIST_URL, params).json()['results']]

        self.assertEqual(names(can_buy='true'), ['Cuaderno', 'Queso'])
        self.assertEqual(names(can_sell='true', active='true'), ['Bolsa', 'Cuaderno'])
        self.assertEqual(names(can_sell='false'), ['Queso'])
        self.assertEqual(names(category='raw_material'), ['Queso'])
        self.assertEqual(names(category='unclassified'), ['Viejo'])
        self.assertEqual(names(category='merchandise', search='cuad', can_buy='true'), ['Cuaderno'])
        for params in ({'category': 'otra'}, {'can_buy': 'si'}, {'can_sell': '1'}):
            self.assertEqual(self.client.get(LIST_URL, params).status_code, 400)

    def test_filters_are_scoped_to_the_company(self):  # INV-07
        ProductModel.objects.create(company_id=uuid4(), name='Ajeno', description='', sale_price=Decimal('1'),
                                    can_buy=True, category='raw_material')
        self.assertEqual(self.client.get(LIST_URL, {'can_buy': 'true'}).json()['results'], [])


class ProductFacadeTests(TestCase):
    def setUp(self):
        self.company_id = uuid4()

    def product(self, **kwargs):
        return ProductModel.objects.create(company_id=self.company_id, name='P', description='', **kwargs)

    def test_purchase_facade_reports_active_and_buyable(self):  # AC-02
        buyable = self.product(can_buy=True, category='raw_material', sale_price=None, can_sell=False)
        inactive = self.product(can_buy=True, active=False, sale_price=None)
        sellable_only = self.product(sale_price=Decimal('1.00'))
        self.assertEqual(get_product_for_purchase(self.company_id, buyable.id),
                         ProductForPurchase(id=buyable.id, name='P', active=True, can_buy=True))
        self.assertFalse(get_product_for_purchase(self.company_id, inactive.id).active)
        self.assertFalse(get_product_for_purchase(self.company_id, sellable_only.id).can_buy)

    def test_purchase_facade_hides_other_companies_and_unknown_ids(self):  # EDGE-05
        other = ProductModel.objects.create(company_id=uuid4(), name='Ajeno', description='', can_buy=True)
        self.assertIsNone(get_product_for_purchase(self.company_id, other.id))
        self.assertIsNone(get_product_for_purchase(self.company_id, uuid4()))

    def test_sale_facade_reports_can_sell(self):  # AC-01
        product = self.product(can_sell=False)
        self.assertFalse(get_product_for_sale(self.company_id, product.id).can_sell)


class ProductUsesMigrationTests(TransactionTestCase):
    """AC-06: las filas previas quedan vendibles, no comprables y sin clasificar, sin tocar stock ni unidad."""

    def test_existing_rows_keep_stock_and_become_sellable_unclassified(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('catalog', '0003_stock_units_warehouses')])
        old_apps = executor.loader.project_state([('catalog', '0003_stock_units_warehouses')]).apps
        old_product = old_apps.get_model('catalog', 'ProductModel')
        old_unit = old_apps.get_model('catalog', 'UnitModel')
        company_id = uuid4()
        unit = old_unit.objects.create(company_id=company_id, name='Kilo', abbreviation='kg')
        row = old_product.objects.create(company_id=company_id, name='Harina', description='',
                                         sale_price=Decimal('7.50'), tracks_stock=True, base_unit=unit)

        executor = MigrationExecutor(connection)
        executor.migrate([('catalog', '0004_product_uses')])
        migrated = ProductModel.objects.get(pk=row.pk)
        self.assertEqual((migrated.can_sell, migrated.can_buy, migrated.category), (True, False, None))
        self.assertEqual((migrated.sale_price, migrated.tracks_stock, migrated.base_unit_id),
                         (Decimal('7.50'), True, unit.pk))

        ProductModel.objects.create(company_id=company_id, name='Insumo', description='', sale_price=None,
                                    can_sell=False)
        executor = MigrationExecutor(connection)
        executor.migrate([('catalog', '0003_stock_units_warehouses')])  # reversa: nulos pasan a 0.00
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
