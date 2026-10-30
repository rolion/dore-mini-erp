"""PB-INV-001 / PB-INV-002: control de stock por producto y unidades de medida."""
from unittest import mock
from uuid import uuid4

from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.catalog.domain.exceptions import UnitInUse, UnitValidationError
from modules.catalog.domain.product import Product
from modules.catalog.domain.unit import UnitOfMeasure
from modules.catalog.infrastructure.django.models import ProductModel
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled
from shared import stock_history

PRODUCTS = '/api/products/'
UNITS = '/api/units/'


class UnitDomainTests(SimpleTestCase):
    def test_create_trims_and_validates(self):  # INV-03
        unit = UnitOfMeasure.create('  Kilogramo ', ' kg ', True)
        self.assertEqual((unit.name, unit.abbreviation, unit.allows_fractions, unit.active), ('Kilogramo', 'kg', True, True))
        with self.assertRaises(UnitValidationError) as ctx:
            UnitOfMeasure.create('', '  ')
        self.assertEqual(set(ctx.exception.errors), {'name', 'abbreviation'})

    def test_used_unit_cannot_change_meaning_but_can_toggle(self):  # INV-04
        unit = UnitOfMeasure.create('Litro', 'l', True)
        unit.in_use = True
        with self.assertRaises(UnitInUse):
            unit.redefine('Litros', 'l', True)
        self.assertFalse(unit.redefine('Litro', 'l', True))  # sin cambios efectivos: permitido
        unit.deactivate()
        self.assertFalse(unit.active)


class ProductStockDomainTests(SimpleTestCase):
    def product(self):
        return Product.create('Harina', '10', category='raw_material')

    def test_default_product_does_not_track_stock(self):  # AC-02
        product = self.product()
        self.assertFalse(product.tracks_stock)
        self.assertIsNone(product.base_unit_id)

    def test_tracking_requires_active_unit(self):  # INV-01
        product, unit = self.product(), UnitOfMeasure.create('Kilogramo', 'kg')
        with self.assertRaises(Exception) as ctx:
            product.configure_stock(True, None)
        self.assertIn('base_unit_id', ctx.exception.errors)
        unit.deactivate()
        with self.assertRaises(Exception):
            product.configure_stock(True, unit)
        unit.activate()
        product.configure_stock(True, unit)
        self.assertEqual(product.base_unit_id, unit.id)
        product.configure_stock(False, None)
        self.assertIsNone(product.base_unit_id)


class StockApiTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))
        set_enabled(self.company, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        self.addCleanup(stock_history.register, None)

    def unit(self, name='Kilogramo', abbreviation='kg', **extra):
        response = self.client.post(UNITS, {'name': name, 'abbreviation': abbreviation, **extra}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def product(self, **extra):
        response = self.client.post(PRODUCTS, {'name': 'Harina', 'sale_price': '10', 'category': 'raw_material', **extra}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()


class UnitApiTests(StockApiTestCase):
    def test_company_starts_without_units(self):  # decisión 1 del usuario
        self.assertEqual(self.client.get(UNITS).json()['results'], [])

    def test_create_list_filter_search(self):  # AC-07
        kg = self.unit()
        self.assertEqual(set(kg), {'id', 'name', 'abbreviation', 'allows_fractions', 'active', 'in_use',
                                   'created_at', 'updated_at'})
        self.assertFalse(kg['allows_fractions'])
        self.unit('Unidad', 'u')
        self.client.post(f"{UNITS}{kg['id']}/deactivate/")
        active = self.client.get(UNITS, {'active': 'true'}).json()['results']
        self.assertEqual([u['name'] for u in active], ['Unidad'])
        self.assertEqual(len(self.client.get(UNITS).json()['results']), 2)
        self.assertEqual([u['name'] for u in self.client.get(UNITS, {'search': 'kilo'}).json()['results']], ['Kilogramo'])

    def test_duplicates_are_rejected_case_insensitively(self):  # INV-03, EDGE-02
        self.unit()
        response = self.client.post(UNITS, {'name': 'KILOGRAMO', 'abbreviation': 'KG'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'name', 'abbreviation'})

    def test_required_fields(self):
        response = self.client.post(UNITS, {'name': ''}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'name', 'abbreviation'})

    def test_used_unit_is_locked_but_can_be_deactivated(self):  # INV-04, AC-07
        kg = self.unit()
        self.product(tracks_stock=True, base_unit_id=kg['id'])
        detail = f"{UNITS}{kg['id']}/"
        self.assertTrue(self.client.get(detail).json()['in_use'])
        response = self.client.patch(detail, {'name': 'Kilos'}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'unit_in_use')
        self.assertEqual(self.client.patch(detail, {'name': 'Kilogramo'}, format='json').status_code, 200)
        self.assertFalse(self.client.post(f'{detail}deactivate/').json()['active'])

    def test_unused_unit_can_be_edited(self):
        kg = self.unit()
        response = self.client.patch(f"{UNITS}{kg['id']}/", {'name': 'Kilos', 'allows_fractions': True}, format='json')
        self.assertEqual((response.status_code, response.json()['name'], response.json()['allows_fractions']),
                         (200, 'Kilos', True))

    def test_other_company_units_are_invisible(self):  # INV-09
        kg = self.unit()
        other = make_company('Empresa B')
        authenticate(self.client, make_admin(other, username='beto'))
        set_enabled(other, ['inventory'])
        self.assertEqual(self.client.get(UNITS).json()['results'], [])
        self.assertEqual(self.client.get(f"{UNITS}{kg['id']}/").status_code, 404)
        self.assertEqual(self.client.post(f"{UNITS}{kg['id']}/deactivate/").status_code, 404)

    def test_units_need_inventory_enabled(self):  # EDGE-04
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)
        self.assertEqual(self.client.get(UNITS).status_code, 403)


class ProductStockApiTests(StockApiTestCase):
    def test_enable_stock_with_unit(self):  # AC-01
        kg = self.unit()
        body = self.product(tracks_stock=True, base_unit_id=kg['id'])
        self.assertTrue(body['tracks_stock'])
        self.assertEqual(body['base_unit'], {'id': kg['id'], 'name': 'Kilogramo', 'abbreviation': 'kg', 'allows_fractions': False})
        listed = self.client.get(PRODUCTS).json()['results'][0]
        self.assertEqual(listed['base_unit']['abbreviation'], 'kg')

    def test_product_without_stock_needs_no_unit(self):  # AC-06
        body = self.product()
        self.assertFalse(body['tracks_stock'])
        self.assertIsNone(body['base_unit_id'])

    def test_stock_without_unit_is_rejected(self):  # AC-04
        response = self.client.post(PRODUCTS, {'name': 'x', 'sale_price': '1', 'category': 'finished', 'tracks_stock': True}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('base_unit_id', response.json())
        self.assertEqual(ProductModel.objects.count(), 0)
        created = self.product()
        response = self.client.patch(f"{PRODUCTS}{created['id']}/", {'tracks_stock': True}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('base_unit_id', response.json())

    def test_inactive_or_foreign_or_unknown_unit_is_rejected(self):  # INV-01, INV-05
        kg = self.unit()
        self.client.post(f"{UNITS}{kg['id']}/deactivate/")
        for unit_id in (kg['id'], str(uuid4())):
            response = self.client.post(
                PRODUCTS, {'name': 'x', 'sale_price': '1', 'category': 'finished', 'tracks_stock': True, 'base_unit_id': unit_id}, format='json')
            self.assertEqual(response.status_code, 400, unit_id)
            self.assertIn('base_unit_id', response.json())

    def test_unit_of_another_company_is_rejected(self):  # INV-09
        other = make_company('Empresa B')
        authenticate(self.client, make_admin(other, username='beto'))
        set_enabled(other, ['inventory'])
        foreign = self.unit('Litro', 'l')
        authenticate(self.client, make_admin(self.company, username='ana2'))
        response = self.client.post(
            PRODUCTS, {'name': 'x', 'sale_price': '1', 'category': 'finished', 'tracks_stock': True, 'base_unit_id': foreign['id']},
            format='json')
        self.assertEqual(response.status_code, 400)

    def test_turning_stock_off_clears_unit(self):  # decisión 7 del ADR
        kg = self.unit()
        created = self.product(tracks_stock=True, base_unit_id=kg['id'])
        body = self.client.patch(f"{PRODUCTS}{created['id']}/", {'tracks_stock': False}, format='json').json()
        self.assertEqual((body['tracks_stock'], body['base_unit_id'], body['base_unit']), (False, None, None))

    def test_history_blocks_changes_with_409(self):  # AC-03, INV-02
        kg, lt = self.unit(), self.unit('Litro', 'l')
        created = self.product(tracks_stock=True, base_unit_id=kg['id'])
        detail = f"{PRODUCTS}{created['id']}/"
        with mock.patch.object(stock_history, '_provider', lambda company_id, product_id: True):
            for payload in ({'base_unit_id': lt['id']}, {'tracks_stock': False}):
                response = self.client.patch(detail, payload, format='json')
                self.assertEqual(response.status_code, 409, payload)
                self.assertEqual(response.json()['code'], 'stock_history_locked')
                self.assertIn('regularización', response.json()['detail'])
            # EDGE-06: lo demás sigue editable y los mismos valores no cuentan como cambio
            ok = self.client.patch(detail, {'name': 'Nuevo', 'tracks_stock': True, 'base_unit_id': kg['id']},
                                   format='json')
            self.assertEqual((ok.status_code, ok.json()['name']), (200, 'Nuevo'))
        stored = self.client.get(detail).json()
        self.assertEqual((stored['tracks_stock'], stored['base_unit_id']), (True, kg['id']))

    def test_without_history_provider_nothing_is_locked(self):
        kg, lt = self.unit(), self.unit('Litro', 'l')
        created = self.product(tracks_stock=True, base_unit_id=kg['id'])
        response = self.client.patch(f"{PRODUCTS}{created['id']}/", {'base_unit_id': lt['id']}, format='json')
        self.assertEqual(response.status_code, 200)

    def test_inventory_disabled_blocks_enabling_but_not_disabling(self):  # INV-08, EDGE-04
        kg = self.unit()
        created = self.product(tracks_stock=True, base_unit_id=kg['id'])
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)
        detail = f"{PRODUCTS}{created['id']}/"
        self.assertEqual(self.client.get(detail).json()['base_unit']['abbreviation'], 'kg')
        response = self.client.post(PRODUCTS, {'name': 'x', 'sale_price': '1', 'category': 'finished', 'tracks_stock': True,
                                               'base_unit_id': kg['id']}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('tracks_stock', response.json())
        self.assertEqual(self.client.patch(detail, {'tracks_stock': False}, format='json').status_code, 200)

    def test_inactive_unit_kept_when_product_is_edited(self):  # EDGE-03
        kg = self.unit()
        created = self.product(tracks_stock=True, base_unit_id=kg['id'])
        self.client.post(f"{UNITS}{kg['id']}/deactivate/")
        response = self.client.patch(
            f"{PRODUCTS}{created['id']}/", {'name': 'Otro', 'tracks_stock': True, 'base_unit_id': kg['id']},
            format='json')
        self.assertEqual(response.status_code, 200, response.content)

    def test_existing_products_default_to_no_stock(self):  # AC-02
        model = ProductModel.objects.create(company_id=self.company.id, name='Viejo', sale_price='1')
        body = self.client.get(f'{PRODUCTS}{model.id}/').json()
        self.assertEqual((body['tracks_stock'], body['base_unit']), (False, None))
