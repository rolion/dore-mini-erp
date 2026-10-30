from dataclasses import FrozenInstanceError
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

from modules.catalog.infrastructure.django.models import ProductModel
from modules.catalog.services import ProductForSale, get_product_for_sale, list_products_for_inventory


COMPANY_ID = uuid4()


class GetProductForSaleTests(TestCase):
    def test_returns_current_name_price_and_state(self):  # AC-21
        product = ProductModel.objects.create(company_id=COMPANY_ID, name='Pack cuñapé', description='', sale_price=Decimal('35.00'))
        self.assertEqual(
            get_product_for_sale(COMPANY_ID, product.id),
            ProductForSale(id=product.id, name='Pack cuñapé', sale_price=Decimal('35.00'), active=True, can_sell=True),
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


class GetProductsForInventoryTests(TestCase):
    def test_returns_tracking_and_unit_of_the_companys_products_only(self):  # PB-INV-004
        from modules.catalog.infrastructure.django.models import UnitModel
        from modules.catalog.services import get_products_for_inventory

        unit = UnitModel.objects.create(company_id=COMPANY_ID, name='Kilogramo', abbreviation='kg', allows_fractions=True)
        tracked = ProductModel.objects.create(
            company_id=COMPANY_ID, name='Arroz', sale_price=Decimal('1.00'), tracks_stock=True, base_unit=unit)
        plain = ProductModel.objects.create(company_id=COMPANY_ID, name='Servicio', sale_price=Decimal('1.00'))
        foreign = ProductModel.objects.create(company_id=uuid4(), name='Ajeno', sale_price=Decimal('1.00'))

        found = get_products_for_inventory(COMPANY_ID, [tracked.id, plain.id, foreign.id, uuid4()])

        self.assertEqual(set(found), {tracked.id, plain.id})
        self.assertEqual((found[tracked.id].tracks_stock, found[tracked.id].unit_abbreviation,
                          found[tracked.id].allows_fractions), (True, 'kg', True))
        self.assertEqual((found[plain.id].tracks_stock, found[plain.id].unit_abbreviation), (False, None))


class ListProductsForInventoryTests(TestCase):
    def make(self, name, company=COMPANY_ID, tracks=True, active=True):
        return ProductModel.objects.create(
            company_id=company, name=name, description='', sale_price=Decimal('1.00'), tracks_stock=tracks,
            active=active)

    def test_lists_only_stock_tracking_products_of_the_company_by_name(self):  # INV-02, INV-03
        self.make('Sal')
        self.make('Azúcar')
        self.make('Servicio', tracks=False)
        self.make('Ajeno', company=uuid4())
        self.assertEqual([p.name for p in list_products_for_inventory(COMPANY_ID)], ['Azúcar', 'Sal'])

    def test_filters_by_search_and_state(self):  # AC-02
        self.make('Harina de trigo')
        self.make('Harina vieja', active=False)
        self.make('Sal')
        names = lambda **kw: [p.name for p in list_products_for_inventory(COMPANY_ID, **kw)]  # noqa: E731
        self.assertEqual(names(search='harina'), ['Harina de trigo', 'Harina vieja'])
        self.assertEqual(names(search='harina', active=False), ['Harina vieja'])
        self.assertEqual(names(active=True), ['Harina de trigo', 'Sal'])

    def test_returns_category_and_uses_and_filters_by_them(self):  # AC-02, AC-03
        def make(name, category, buy, sell, company=COMPANY_ID):
            ProductModel.objects.create(
                company_id=company, name=name, sale_price=Decimal('1.00') if sell else None, tracks_stock=True,
                category=category, can_buy=buy, can_sell=sell)
        make('Cuñapé', 'intermediate', False, False)
        make('Bolsa', 'packaging', True, False)
        make('Cuaderno', 'merchandise', True, True)
        make('Viejo', None, False, True)
        make('Ajeno', 'packaging', True, False, company=uuid4())
        names = lambda **kw: [p.name for p in list_products_for_inventory(COMPANY_ID, **kw)]  # noqa: E731
        self.assertEqual(names(category='intermediate', can_sell=False), ['Cuñapé'])
        self.assertEqual(names(category='packaging', can_buy=True), ['Bolsa'])
        self.assertEqual(names(can_buy=True, can_sell=True), ['Cuaderno'])
        self.assertEqual(names(category='none'), ['Viejo'])
        self.assertEqual(names(can_buy=False, can_sell=False), ['Cuñapé'])
        bolsa = next(p for p in list_products_for_inventory(COMPANY_ID) if p.name == 'Bolsa')
        self.assertEqual((bolsa.category, bolsa.can_buy, bolsa.can_sell), ('packaging', True, False))


class GetProductsForPurchaseTests(TestCase):
    def test_returns_name_state_and_unit_of_the_companys_products_only(self):  # PB-COM-002 INV-04, INV-11
        from modules.catalog.infrastructure.django.models import UnitModel
        from modules.catalog.services import ProductForPurchase, get_products_for_purchase
        unit = UnitModel.objects.create(company_id=COMPANY_ID, name='Kilogramo', abbreviation='kg', allows_fractions=True)
        with_unit = ProductModel.objects.create(company_id=COMPANY_ID, name='Arroz', sale_price=Decimal('1.00'),
                                                tracks_stock=True, base_unit=unit, can_buy=True)
        bare = ProductModel.objects.create(company_id=COMPANY_ID, name='Bolsa', sale_price=Decimal('1.00'), active=False)
        foreign = ProductModel.objects.create(company_id=uuid4(), name='Ajeno', sale_price=Decimal('1.00'))
        result = get_products_for_purchase(COMPANY_ID, [with_unit.id, bare.id, foreign.id, uuid4()])
        self.assertEqual(result, {
            with_unit.id: ProductForPurchase(with_unit.id, 'Arroz', True, True, 'kg', True),
            bare.id: ProductForPurchase(bare.id, 'Bolsa', False, False, None, False),
        })
