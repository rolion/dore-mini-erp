from uuid import uuid4

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from modules.catalog.infrastructure.django.models import ProductModel

LIST_URL = '/api/products/'


def detail_url(product_id, suffix=''):
    return f'/api/products/{product_id}/{suffix}'


class ProductApiTestCase(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='ana', password='x-Pass-123')
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def create(self, name='Cuñapé', sale_price='10.00', **extra):
        response = self.client.post(LIST_URL, {'name': name, 'sale_price': sale_price, **extra}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()


class CreateProductTests(ProductApiTestCase):
    def test_create_valid_returns_active_product_in_list(self):  # AC-01
        body = self.create(name='  Pack 10  ', sale_price='35', description='Tradicional')
        self.assertEqual(body['name'], 'Pack 10')
        self.assertEqual(body['sale_price'], '35.00')
        self.assertEqual(body['description'], 'Tradicional')
        self.assertTrue(body['active'])
        self.assertEqual(set(body), {'id', 'name', 'description', 'sale_price', 'active', 'created_at', 'updated_at'})
        listed = self.client.get(LIST_URL).json()['results']
        self.assertEqual([p['id'] for p in listed], [body['id']])

    def test_create_ignores_active_in_body(self):  # INV-03 / INV-04
        body = self.create(active=False)
        self.assertTrue(body['active'])

    def test_price_zero_is_valid(self):  # AC-03
        self.assertEqual(self.create(sale_price='0')['sale_price'], '0.00')
        self.assertEqual(self.create(sale_price=0)['sale_price'], '0.00')

    def test_invalid_name_is_rejected(self):  # AC-02
        for payload in ({'sale_price': '1'}, {'name': '', 'sale_price': '1'}, {'name': '   ', 'sale_price': '1'},
                        {'name': 'a' * 151, 'sale_price': '1'}, {'name': None, 'sale_price': '1'}):
            response = self.client.post(LIST_URL, payload, format='json')
            self.assertEqual(response.status_code, 400, payload)
            self.assertIn('name', response.json())
        self.assertEqual(ProductModel.objects.count(), 0)

    def test_name_of_150_chars_is_valid(self):  # EDGE-01
        self.create(name='a' * 150)

    def test_invalid_price_is_rejected(self):  # AC-03 / EDGE-02
        for price in (None, '', 'abc', '-1', '35.555', '10000000000.00'):
            response = self.client.post(LIST_URL, {'name': 'x', 'sale_price': price}, format='json')
            self.assertEqual(response.status_code, 400, price)
            self.assertIn('sale_price', response.json())
        response = self.client.post(LIST_URL, {'name': 'x'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('sale_price', response.json())
        self.assertEqual(ProductModel.objects.count(), 0)

    def test_price_formats_accepted(self):  # EDGE-02
        self.assertEqual(self.create(sale_price='35.5')['sale_price'], '35.50')
        self.assertEqual(self.create(sale_price='9999999999.99')['sale_price'], '9999999999.99')

    def test_duplicate_names_allowed(self):  # EDGE-04
        self.create(name='Igual')
        self.create(name='Igual')
        self.assertEqual(ProductModel.objects.count(), 2)


class UpdateProductTests(ProductApiTestCase):
    def test_patch_updates_fields_and_refreshes_updated_at(self):  # AC-04
        created = self.create(description='original')
        response = self.client.patch(
            detail_url(created['id']), {'name': 'Nuevo', 'sale_price': '12.5'}, format='json')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body['name'], body['sale_price'], body['description']), ('Nuevo', '12.50', 'original'))
        self.assertGreater(body['updated_at'], created['updated_at'])
        self.assertEqual(body['created_at'], created['created_at'])
        self.assertEqual(self.client.get(detail_url(created['id'])).json(), body)
        self.assertEqual(self.client.get(LIST_URL).json()['results'][0]['name'], 'Nuevo')

    def test_patch_description_can_be_cleared(self):
        created = self.create(description='algo')
        response = self.client.patch(detail_url(created['id']), {'description': ''}, format='json')
        self.assertEqual(response.json()['description'], '')

    def test_patch_ignores_active(self):  # AC-04 / INV-04
        created = self.create()
        response = self.client.patch(detail_url(created['id']), {'active': False}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['active'])

    def test_patch_invalid_values_rejected_and_nothing_saved(self):  # AC-03 / EDGE-03
        created = self.create(name='Original', sale_price='10')
        response = self.client.patch(detail_url(created['id']), {'name': '', 'sale_price': '-1'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'name', 'sale_price'})
        stored = self.client.get(detail_url(created['id'])).json()
        self.assertEqual((stored['name'], stored['sale_price']), ('Original', '10.00'))

    def test_patch_empty_body_is_noop(self):  # EDGE-03
        created = self.create()
        response = self.client.patch(detail_url(created['id']), {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), created)

    def test_patch_unknown_product_is_404(self):  # AC-07
        response = self.client.patch(detail_url(uuid4()), {'name': 'x'}, format='json')
        self.assertEqual(response.status_code, 404)


class ActivationTests(ProductApiTestCase):
    def test_deactivate_keeps_product_visible_and_activate_restores(self):  # AC-05
        created = self.create()
        response = self.client.post(detail_url(created['id'], 'deactivate/'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['active'])
        self.assertEqual(self.client.post(detail_url(created['id'], 'deactivate/')).status_code, 200)
        self.assertFalse(self.client.get(detail_url(created['id'])).json()['active'])
        self.assertEqual(len(self.client.get(LIST_URL).json()['results']), 1)
        self.assertEqual(len(self.client.get(LIST_URL, {'active': 'false'}).json()['results']), 1)
        self.assertEqual(len(self.client.get(LIST_URL, {'active': 'true'}).json()['results']), 0)
        response = self.client.post(detail_url(created['id'], 'activate/'))
        self.assertTrue(response.json()['active'])
        self.assertTrue(self.client.post(detail_url(created['id'], 'activate/')).json()['active'])

    def test_unknown_product_is_404(self):  # AC-07
        for suffix in ('activate/', 'deactivate/'):
            self.assertEqual(self.client.post(detail_url(uuid4(), suffix)).status_code, 404)


class ListProductTests(ProductApiTestCase):
    def test_empty_list(self):  # EDGE-06
        body = self.client.get(LIST_URL).json()
        self.assertEqual((body['count'], body['results']), (0, []))

    def test_orders_by_name_and_filters(self):  # AC-06
        grande = self.create(name='Cuñapé grande')
        self.create(name='chipa')
        self.create(name='Alfajor')
        self.client.post(detail_url(grande['id'], 'deactivate/'))
        names = lambda **params: [p['name'] for p in self.client.get(LIST_URL, params).json()['results']]  # noqa: E731
        self.assertEqual(names(), ['Alfajor', 'chipa', 'Cuñapé grande'])
        self.assertEqual(names(search='CHIPA'), ['chipa'])
        self.assertEqual(names(search='  ap  '), ['Cuñapé grande'])
        self.assertEqual(names(search=''), ['Alfajor', 'chipa', 'Cuñapé grande'])
        self.assertEqual(names(active='true'), ['Alfajor', 'chipa'])
        self.assertEqual(names(active='false'), ['Cuñapé grande'])
        self.assertEqual(names(active='false', search='alf'), [])

    def test_invalid_active_value_is_400(self):  # EDGE-05
        response = self.client.get(LIST_URL, {'active': 'foo'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('active', response.json())

    def test_pagination(self):  # AC-06
        for i in range(5):
            self.create(name=f'P{i}')
        body = self.client.get(LIST_URL, {'page_size': 2}).json()
        self.assertEqual(body['count'], 5)
        self.assertEqual([p['name'] for p in body['results']], ['P0', 'P1'])
        self.assertIsNotNone(body['next'])
        self.assertIsNone(body['previous'])
        body = self.client.get(LIST_URL, {'page_size': 2, 'page': 3}).json()
        self.assertEqual([p['name'] for p in body['results']], ['P4'])
        self.assertEqual(self.client.get(LIST_URL, {'page_size': 2, 'page': 4}).status_code, 404)

    def test_page_size_is_capped(self):  # AC-06
        body = self.client.get(LIST_URL, {'page_size': 1000}).json()
        self.assertEqual(body['count'], 0)


class DetailTests(ProductApiTestCase):
    def test_detail_returns_all_fields(self):  # AC-07
        created = self.create(description='d')
        response = self.client.get(detail_url(created['id']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), created)

    def test_unknown_or_malformed_id_is_404(self):  # AC-07
        self.assertEqual(self.client.get(detail_url(uuid4())).status_code, 404)
        self.assertEqual(self.client.get('/api/products/not-a-uuid/').status_code, 404)


class AccessTests(ProductApiTestCase):
    def test_delete_and_put_not_allowed(self):  # AC-08 / INV-05
        created = self.create()
        self.assertEqual(self.client.delete(detail_url(created['id'])).status_code, 405)
        self.assertEqual(self.client.put(detail_url(created['id']), {'name': 'x'}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(LIST_URL).status_code, 405)
        self.assertEqual(ProductModel.objects.count(), 1)

    def test_requires_token(self):  # AC-08
        created = self.create()
        self.client.credentials()
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)
        self.assertEqual(self.client.post(LIST_URL, {'name': 'x', 'sale_price': '1'}, format='json').status_code, 401)
        self.assertEqual(self.client.get(detail_url(created['id'])).status_code, 401)
        self.assertEqual(self.client.patch(detail_url(created['id']), {}, format='json').status_code, 401)
        self.assertEqual(self.client.post(detail_url(created['id'], 'deactivate/')).status_code, 401)
        self.assertEqual(self.client.post(detail_url(created['id'], 'activate/')).status_code, 401)
