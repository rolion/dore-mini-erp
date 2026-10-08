from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.catalog.application.commands import (
    ActivateProduct,
    CreateProduct,
    DeactivateProduct,
    UpdateProduct,
)
from modules.catalog.application.queries import GetProduct, ListProducts
from modules.catalog.domain.exceptions import ProductNotFound, ProductValidationError


class InMemoryProductRepository:
    def __init__(self):
        self.items = {}
        self.saves = 0

    def get(self, product_id):
        return self.items.get(product_id)

    def save(self, product):
        self.saves += 1
        self.items[product.id] = product
        return product

    def list(self, search=None, active=None):
        products = sorted(self.items.values(), key=lambda p: (p.name, str(p.id)))
        if search:
            products = [p for p in products if search.lower() in p.name.lower()]
        if active is not None:
            products = [p for p in products if p.active is active]
        return products


class CatalogUseCaseTests(SimpleTestCase):
    def setUp(self):
        self.repo = InMemoryProductRepository()

    def create(self, name='Cuñapé', price='10', **extra):
        return CreateProduct(self.repo).execute(name=name, sale_price=price, **extra)

    def test_create_saves_active_product(self):  # AC-01
        product = self.create()
        self.assertTrue(product.active)
        self.assertIs(self.repo.get(product.id), product)

    def test_create_invalid_does_not_save(self):  # AC-02, AC-03
        with self.assertRaises(ProductValidationError):
            self.create(name='')
        with self.assertRaises(ProductValidationError):
            self.create(price='-1')
        self.assertEqual(self.repo.saves, 0)

    def test_update_partial_changes_only_given_fields(self):  # AC-04
        product = self.create(description='original')
        updated = UpdateProduct(self.repo).execute(product.id, sale_price='15')
        self.assertEqual((updated.name, updated.description, updated.sale_price),
                         ('Cuñapé', 'original', Decimal('15.00')))

    def test_update_invalid_does_not_save_and_collects_errors(self):  # AC-03, EDGE-03
        product = self.create()
        saves = self.repo.saves
        with self.assertRaises(ProductValidationError) as ctx:
            UpdateProduct(self.repo).execute(product.id, name='', sale_price='-1')
        self.assertEqual(set(ctx.exception.errors), {'name', 'sale_price'})
        self.assertEqual(self.repo.saves, saves)

    def test_update_without_changes_does_not_save(self):  # EDGE-03
        product = self.create()
        saves = self.repo.saves
        UpdateProduct(self.repo).execute(product.id)
        self.assertEqual(self.repo.saves, saves)

    def test_update_does_not_change_active_state(self):  # INV-04
        product = self.create()
        DeactivateProduct(self.repo).execute(product.id)
        updated = UpdateProduct(self.repo).execute(product.id, name='Otro')
        self.assertFalse(updated.active)

    def test_deactivate_keeps_product_and_activate_restores(self):  # AC-05
        product = self.create()
        self.assertFalse(DeactivateProduct(self.repo).execute(product.id).active)
        self.assertFalse(DeactivateProduct(self.repo).execute(product.id).active)
        self.assertIs(GetProduct(self.repo).execute(product.id), product)
        self.assertTrue(ActivateProduct(self.repo).execute(product.id).active)

    def test_not_found(self):  # AC-07
        missing = uuid4()
        for use_case, kwargs in (
            (GetProduct, {}), (UpdateProduct, {'name': 'x'}), (ActivateProduct, {}), (DeactivateProduct, {}),
        ):
            with self.assertRaises(ProductNotFound):
                use_case(self.repo).execute(missing, **kwargs)

    def test_list_filters_by_search_and_state(self):  # AC-06
        a = self.create(name='Cuñapé grande')
        self.create(name='Chipa')
        DeactivateProduct(self.repo).execute(a.id)
        names = lambda **kw: [p.name for p in ListProducts(self.repo).execute(**kw)]  # noqa: E731
        self.assertEqual(names(), ['Chipa', 'Cuñapé grande'])
        self.assertEqual(names(search='CUÑAPÉ'), ['Cuñapé grande'])
        self.assertEqual(names(active=True), ['Chipa'])
        self.assertEqual(names(active=False), ['Cuñapé grande'])
        self.assertEqual(names(search='chi', active=False), [])
