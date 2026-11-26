from decimal import Decimal
from uuid import uuid4

from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.catalog.infrastructure.django.models import ProductModel, UnitModel
from modules.catalog.services import get_products_for_production
from modules.modularity.infrastructure.django.models import CompanyModuleModel, CompanySettingsModel
from modules.production.infrastructure.django.models import RecipeModel

URL = '/api/recipes/'


class RecipeApiTests(APITestCase):
    def setUp(self):
        self.company = make_company('Producción A')
        self.user = make_admin(self.company, username='prod-admin')
        authenticate(self.client, self.user)
        CompanySettingsModel.objects.create(company_id=self.company.id)
        CompanyModuleModel.objects.create(company_id=self.company.id, module_key='production')
        self.unit = UnitModel.objects.create(company_id=self.company.id, name='Unidad', abbreviation='u')
        self.kilo = UnitModel.objects.create(company_id=self.company.id, name='Kilogramo', abbreviation='kg',
                                             allows_fractions=True)
        self.result = self.product('Cuñapé a granel', self.unit)
        self.cheese = self.product('Queso', self.kilo)
        self.flour = self.product('Almidón', self.kilo)

    def product(self, name, unit, company=None, **extra):
        return ProductModel.objects.create(company_id=(company or self.company).id, name=name, base_unit=unit,
                                           sale_price=Decimal('1.00'), **extra)

    def payload(self, **changes):
        body = {'name': 'Queso', 'result_product_id': str(self.result.id), 'yield_quantity': '24',
                'ingredients': [{'product_id': str(self.cheese.id), 'unit_id': str(self.kilo.id), 'quantity': '1.5'},
                                {'product_id': str(self.flour.id), 'unit_id': str(self.kilo.id), 'quantity': '2'}]}
        body.update(changes)
        return body

    def create(self, **changes):
        response = self.client.post(URL, self.payload(**changes), format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_create_list_and_detail(self):  # AC-01, AC-03, AC-04, INV-07
        body = self.create(company_id=str(uuid4()), active=False)
        self.assertTrue(body['active'])
        self.assertEqual(body['yield_quantity'], '24.0000')
        self.assertEqual(body['result_product']['unit']['abbreviation'], 'u')
        self.assertEqual([(i['product_name'], i['quantity'], i['unit_abbreviation']) for i in body['ingredients']],
                         [('Queso', '1.5000', 'kg'), ('Almidón', '2.0000', 'kg')])
        self.assertEqual(RecipeModel.objects.get(pk=body['id']).company_id, self.company.id)
        self.assertEqual(self.client.get(f"{URL}{body['id']}/").json(), body)
        self.assertEqual(self.client.get(URL).json()['results'], [body])

    def test_validation_errors_by_field_and_line(self):  # AC-02
        cases = [
            ({'name': '  '}, 'name'),
            ({'yield_quantity': '0'}, 'yield_quantity'),
            ({'yield_quantity': 24.5}, 'yield_quantity'),
            ({'yield_quantity': '2.5'}, 'yield_quantity'),  # unidad entera
            ({'result_product_id': str(uuid4())}, 'result_product_id'),
            ({'ingredients': []}, 'ingredients'),
        ]
        for changes, field in cases:
            with self.subTest(changes=changes):
                response = self.client.post(URL, self.payload(**changes), format='json')
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(field, response.json())
        line = {'product_id': str(self.cheese.id), 'unit_id': str(self.kilo.id), 'quantity': '1'}
        for bad, field in (({'quantity': '0'}, 'quantity'), ({'unit_id': str(self.unit.id)}, 'unit_id'),
                           ({'product_id': str(uuid4())}, 'product_id'),
                           ({'product_id': str(self.result.id)}, 'product_id')):
            with self.subTest(line=bad):
                response = self.client.post(URL, self.payload(ingredients=[{**line, **bad}]), format='json')
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(field, response.json()['ingredients'][0])
        repeated = self.client.post(URL, self.payload(ingredients=[line, line]), format='json')
        self.assertIn('product_id', repeated.json()['ingredients'][1])
        self.assertEqual(RecipeModel.objects.count(), 0)

    def test_fractions_rejected_for_integer_unit_ingredient(self):  # INV-04
        eggs = self.product('Huevo', self.unit)
        line = {'product_id': str(eggs.id), 'unit_id': str(self.unit.id), 'quantity': '1.5'}
        response = self.client.post(URL, self.payload(ingredients=[line]), format='json')
        self.assertIn('quantity', response.json()['ingredients'][0])

    def test_inactive_and_unitless_products_rejected(self):  # INV-02, INV-04
        old = self.product('Viejo', self.kilo, active=False)
        bare = ProductModel.objects.create(company_id=self.company.id, name='Sin unidad', sale_price=Decimal('1'))
        for product, key in ((old, 'result_product_id'), (bare, 'result_product_id')):
            response = self.client.post(URL, self.payload(result_product_id=str(product.id)), format='json')
            self.assertIn(key, response.json())
        line = {'product_id': str(old.id), 'unit_id': str(self.kilo.id), 'quantity': '1'}
        self.assertEqual(self.client.post(URL, self.payload(ingredients=[line]), format='json').status_code, 400)

    def test_name_unique_per_company_case_insensitive(self):  # INV-01, EDGE-01
        self.create()
        duplicate = self.client.post(URL, self.payload(name='  qUESO '), format='json')
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn('name', duplicate.json())
        other = make_company('Producción B')
        with self.assertRaises(IntegrityError), transaction.atomic():
            RecipeModel.objects.create(company_id=self.company.id, name='QUESO', result_product_id=uuid4(),
                                       yield_quantity=1)
        RecipeModel.objects.create(company_id=other.id, name='Queso', result_product_id=uuid4(), yield_quantity=1)

    def test_update_replaces_definition_keeping_identity(self):  # AC-05
        body = self.create()
        eggs = self.product('Huevo', self.unit)
        changes = self.payload(name='Queso 2', yield_quantity='12', ingredients=[
            {'product_id': str(eggs.id), 'unit_id': str(self.unit.id), 'quantity': '3'}])
        response = self.client.put(f"{URL}{body['id']}/", changes, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        updated = response.json()
        self.assertEqual((updated['id'], updated['created_at'], updated['name']),
                         (body['id'], body['created_at'], 'Queso 2'))
        self.assertEqual([i['product_name'] for i in updated['ingredients']], ['Huevo'])
        again = self.client.put(f"{URL}{body['id']}/", changes, format='json')
        self.assertEqual(again.status_code, 200)

    def test_activate_deactivate_idempotent_and_filters(self):  # AC-03, AC-06
        body = self.create()
        for _ in range(2):
            response = self.client.post(f"{URL}{body['id']}/deactivate/")
            self.assertEqual((response.status_code, response.json()['active']), (200, False))
        self.assertEqual(self.client.get(URL).json()['count'], 0)
        self.assertEqual(self.client.get(URL, {'status': 'inactive'}).json()['count'], 1)
        self.assertEqual(self.client.get(URL, {'status': 'all', 'q': 'ques'}).json()['count'], 1)
        self.assertEqual(self.client.get(URL, {'status': 'all', 'q': 'zzz'}).json()['count'], 0)
        for _ in range(2):
            self.assertTrue(self.client.post(f"{URL}{body['id']}/activate/").json()['active'])
        self.assertEqual(self.client.get(f"{URL}{body['id']}/").json()['ingredients'], body['ingredients'])
        self.assertEqual(self.client.get(URL, {'status': 'nope'}).status_code, 400)
        self.assertEqual(self.client.get(URL, {'page': '0'}).status_code, 400)

    def test_no_delete(self):  # AC-07
        body = self.create()
        self.assertEqual(self.client.delete(f"{URL}{body['id']}/").status_code, 405)
        self.assertEqual(RecipeModel.objects.count(), 1)

    def test_other_company_recipe_is_not_found(self):  # AC-08, INV-07
        other = make_company('Producción B')
        recipe = RecipeModel.objects.create(company_id=other.id, name='Ajena', result_product_id=uuid4(),
                                            yield_quantity=1)
        for method, suffix in (('get', ''), ('put', ''), ('post', 'activate/'), ('post', 'deactivate/')):
            response = getattr(self.client, method)(f'{URL}{recipe.id}/{suffix}', self.payload(), format='json')
            self.assertEqual(response.status_code, 404, (method, suffix))
        self.assertEqual(self.client.get(URL, {'status': 'all'}).json()['count'], 0)

    def test_foreign_company_products_are_rejected(self):  # AC-02, INV-07
        other = make_company('Producción B')
        foreign = self.product('Ajeno', self.kilo, company=other)
        response = self.client.post(URL, self.payload(result_product_id=str(foreign.id)), format='json')
        self.assertIn('result_product_id', response.json())

    def test_authentication_and_module_gate(self):  # AC-08, AC-09
        self.client.credentials()
        self.assertEqual(self.client.get(URL).status_code, 401)
        authenticate(self.client, self.user)
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='production').delete()
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'module_disabled')

    def test_catalog_facade_for_production(self):  # fachada de Catálogo
        found = get_products_for_production(self.company.id, [self.cheese.id, uuid4()])
        self.assertEqual(list(found), [self.cheese.id])
        dto = found[self.cheese.id]
        self.assertEqual((dto.name, dto.unit_id, dto.unit_abbreviation, dto.allows_fractions, dto.active),
                         ('Queso', self.kilo.id, 'kg', True, True))
        self.assertEqual(get_products_for_production(uuid4(), [self.cheese.id]), {})
