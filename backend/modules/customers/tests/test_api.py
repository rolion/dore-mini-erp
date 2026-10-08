from uuid import uuid4

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from modules.customers.infrastructure.django.models import CustomerModel

LIST_URL = '/api/customers/'


def detail_url(customer_id, suffix=''):
    return f'/api/customers/{customer_id}/{suffix}'


class CustomerApiTestCase(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='ana', password='x-Pass-123')
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def create(self, name='Ana Pérez', **extra):
        response = self.client.post(LIST_URL, {'name': name, **extra}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()


class CreateCustomerTests(CustomerApiTestCase):
    def test_create_with_name_only(self):  # AC-01
        body = self.create(name='  Ana  ')
        self.assertEqual(body['name'], 'Ana')
        self.assertEqual((body['phone'], body['email'], body['notes']), ('', '', ''))
        self.assertTrue(body['active'])
        self.assertEqual(
            set(body), {'id', 'name', 'phone', 'email', 'notes', 'active', 'created_at', 'updated_at'})
        listed = self.client.get(LIST_URL).json()['results']
        self.assertEqual([c['id'] for c in listed], [body['id']])

    def test_create_ignores_active_in_body(self):  # INV-04
        self.assertTrue(self.create(active=False)['active'])

    def test_create_normalizes_phone(self):  # AC-03
        for raw in ('76543210', '+591 7654-3210', '(591) 76543210', '591 76543210', '00591 76543210'):
            CustomerModel.objects.all().delete()
            self.assertEqual(self.create(phone=raw)['phone'], '+59176543210', raw)

    def test_not_normalizable_phone_is_stored_as_is(self):  # AC-03
        self.assertEqual(self.create(phone='  abc  ')['phone'], 'abc')

    def test_invalid_name(self):  # AC-02
        for name in ('', '   ', 'a' * 151):
            response = self.client.post(LIST_URL, {'name': name}, format='json')
            self.assertEqual(response.status_code, 400, name)
            self.assertIn('name', response.json())
        response = self.client.post(LIST_URL, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.json())
        self.assertEqual(CustomerModel.objects.count(), 0)

    def test_invalid_name_is_reported_together_with_other_fields(self):  # AC-02, EDGE-10
        for name in ('', '   ', 'a' * 151):
            response = self.client.post(
                LIST_URL, {'name': name, 'email': 'mal', 'phone': 'x' * 31, 'notes': 'n' * 2001}, format='json')
            self.assertEqual(response.status_code, 400, name)
            self.assertEqual(set(response.json()), {'name', 'email', 'phone', 'notes'}, name)
        response = self.client.post(LIST_URL, {'email': 'mal'}, format='json')
        self.assertEqual(set(response.json()), {'name', 'email'})
        self.assertEqual(response.json()['name'], ['El nombre es obligatorio.'])
        self.assertEqual(CustomerModel.objects.count(), 0)

    def test_invalid_email_phone_notes_report_all_errors_together(self):  # AC-02
        response = self.client.post(
            LIST_URL,
            {'name': 'Ana', 'email': 'mal', 'phone': 'x' * 31, 'notes': 'n' * 2001},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'email', 'phone', 'notes'})
        self.assertEqual(CustomerModel.objects.count(), 0)


class DuplicatePhoneTests(CustomerApiTestCase):
    def test_duplicate_without_confirmation_returns_409_and_creates_nothing(self):  # AC-04, EDGE-02
        first = self.create(name='Ana', phone='76543210')
        response = self.client.post(LIST_URL, {'name': 'Otra', 'phone': '+591 7654-3210'}, format='json')
        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body['code'], 'duplicate_phone')
        self.assertIn('detail', body)
        self.assertEqual(body['matches'], [
            {'id': first['id'], 'name': 'Ana', 'phone': '+59176543210', 'active': True},
        ])
        self.assertEqual(CustomerModel.objects.count(), 1)

    def test_all_formats_of_the_same_number_are_duplicates(self):  # EDGE-02
        self.create(name='Ana', phone='(591) 76543210')
        for raw in ('76543210', '+591 76543210', '591 76543210', '00591 7654 3210'):
            response = self.client.post(LIST_URL, {'name': 'Otra', 'phone': raw}, format='json')
            self.assertEqual(response.status_code, 409, raw)
            self.assertEqual(response.json()['matches'][0]['phone'], '+59176543210', raw)
        self.assertEqual(CustomerModel.objects.count(), 1)

    def test_duplicate_with_confirmation_creates(self):  # AC-04, INV-06
        self.create(name='Ana', phone='76543210')
        body = self.create(name='Otra', phone='76543210', confirm_duplicate=True)
        self.assertNotIn('confirm_duplicate', body)
        self.assertEqual(CustomerModel.objects.filter(phone='+59176543210').count(), 2)

    def test_inactive_customer_also_matches(self):  # EDGE-03
        first = self.create(name='Ana', phone='76543210')
        self.client.post(detail_url(first['id'], 'deactivate/'))
        response = self.client.post(LIST_URL, {'name': 'Otra', 'phone': '76543210'}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertIs(response.json()['matches'][0]['active'], False)

    def test_no_phone_never_conflicts(self):  # AC-04
        self.create(name='A')
        self.create(name='B')

    def test_matches_are_limited_to_ten(self):  # EDGE-05
        for i in range(12):
            self.create(name=f'C{i:02d}', phone='76543210', confirm_duplicate=True)
        response = self.client.post(LIST_URL, {'name': 'Nuevo', 'phone': '76543210'}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(response.json()['matches']), 10)

    def test_confirmation_without_duplicate_creates_normally(self):  # EDGE-09
        self.create(phone='76543210', confirm_duplicate=True)

    def test_database_has_no_unique_constraint_on_phone(self):  # INV-06
        CustomerModel.objects.create(name='A', phone='+59176543210')
        CustomerModel.objects.create(name='B', phone='+59176543210')
        self.assertEqual(CustomerModel.objects.count(), 2)


class UpdateCustomerTests(CustomerApiTestCase):
    def test_patch_updates_only_sent_fields(self):  # AC-05
        created = self.create(name='Ana', phone='76543210', email='a@x.com', notes='n')
        response = self.client.patch(detail_url(created['id']), {'name': 'Beatriz', 'notes': 'vip'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['name'], body['phone'], body['email'], body['notes']),
                         ('Beatriz', '+59176543210', 'a@x.com', 'vip'))
        self.assertEqual(body['id'], created['id'])
        self.assertEqual(body['created_at'], created['created_at'])
        self.assertGreaterEqual(body['updated_at'], created['updated_at'])
        self.assertEqual(self.client.get(detail_url(created['id'])).json(), body)

    def test_patch_phone_normalizes_and_clears(self):  # AC-03, EDGE-07
        created = self.create(phone='76543210')
        body = self.client.patch(detail_url(created['id']), {'phone': '71111111'}, format='json').json()
        self.assertEqual(body['phone'], '+59171111111')
        body = self.client.patch(detail_url(created['id']), {'phone': ''}, format='json').json()
        self.assertEqual(body['phone'], '')

    def test_patch_empty_body_and_ignored_active(self):  # AC-05
        created = self.create(name='Ana')
        response = self.client.patch(detail_url(created['id']), {'active': False}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['active'])
        self.assertEqual(self.client.patch(detail_url(created['id']), {}, format='json').status_code, 200)

    def test_patch_empty_name_is_error_and_changes_nothing(self):  # EDGE-07, AC-02
        created = self.create(name='Ana')
        response = self.client.patch(detail_url(created['id']), {'name': ''}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(detail_url(created['id'])).json()['name'], 'Ana')

    def test_patch_does_not_check_duplicates(self):  # AC-05
        self.create(name='Ana', phone='76543210')
        other = self.create(name='Otra', phone='71111111')
        response = self.client.patch(detail_url(other['id']), {'phone': '76543210'}, format='json')
        self.assertEqual(response.status_code, 200)

    def test_patch_unknown_returns_404(self):  # AC-08
        response = self.client.patch(detail_url(uuid4()), {'name': 'x'}, format='json')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'detail': 'Cliente no encontrado.'})


class ListCustomersTests(CustomerApiTestCase):
    def names(self, query=''):
        response = self.client.get(f'{LIST_URL}{query}')
        self.assertEqual(response.status_code, 200, response.content)
        return [c['name'] for c in response.json()['results']]

    def setUp(self):
        super().setUp()
        self.ana = self.create(name='Ana Pérez', phone='76543210')
        self.beto = self.create(name='Beto Gómez', phone='71111111')
        self.carla = self.create(name='Carla', phone='+34 600 123 456')
        self.client.post(detail_url(self.carla['id'], 'deactivate/'))

    def test_list_is_ordered_by_name(self):  # AC-06
        self.assertEqual(self.names(), ['Ana Pérez', 'Beto Gómez', 'Carla'])

    def test_search_by_name_is_partial_and_case_insensitive(self):  # AC-06
        self.assertEqual(self.names('?search=BETO'), ['Beto Gómez'])
        self.assertEqual(self.names('?search=rez'), ['Ana Pérez'])

    def test_search_by_phone_ignores_separators(self):  # AC-06
        self.assertEqual(self.names('?search=765%20432'), ['Ana Pérez'])
        self.assertEqual(self.names('?search=%2B591%207111'), ['Beto Gómez'])
        self.assertEqual(self.names('?search=600-123'), ['Carla'])

    def test_search_without_digits_only_matches_name(self):  # EDGE-06
        self.assertEqual(self.names('?search=zzz'), [])

    def test_empty_search_does_not_filter(self):  # EDGE-06
        self.assertEqual(len(self.names('?search=')), 3)

    def test_filter_by_active(self):  # AC-06, AC-07
        self.assertEqual(self.names('?active=true'), ['Ana Pérez', 'Beto Gómez'])
        self.assertEqual(self.names('?active=false'), ['Carla'])
        self.assertEqual(self.names('?search=a&active=true'), ['Ana Pérez'])

    def test_invalid_active_is_400(self):  # EDGE-06
        self.assertEqual(self.client.get(f'{LIST_URL}?active=maybe').status_code, 400)

    def test_pagination_and_page_size_cap(self):  # AC-06
        body = self.client.get(f'{LIST_URL}?page_size=2').json()
        self.assertEqual((body['count'], len(body['results'])), (3, 2))
        self.assertIsNotNone(body['next'])
        self.assertEqual(self.names('?page_size=2&page=2'), ['Carla'])
        for i in range(105):
            CustomerModel.objects.create(name=f'Z{i:03d}')
        body = self.client.get(f'{LIST_URL}?page_size=500').json()
        self.assertEqual(len(body['results']), 100)


class ActivateDeactivateTests(CustomerApiTestCase):
    def test_deactivate_keeps_customer_and_is_idempotent(self):  # AC-07
        created = self.create(name='Ana')
        for _ in range(2):
            response = self.client.post(detail_url(created['id'], 'deactivate/'))
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()['active'])
        self.assertFalse(self.client.get(detail_url(created['id'])).json()['active'])
        self.assertEqual(self.client.get(f'{LIST_URL}?active=true').json()['results'], [])
        self.assertEqual(len(self.client.get(f'{LIST_URL}?active=false').json()['results']), 1)
        self.assertEqual(len(self.client.get(LIST_URL).json()['results']), 1)

    def test_activate_restores_and_is_idempotent(self):  # AC-07
        created = self.create(name='Ana')
        self.client.post(detail_url(created['id'], 'deactivate/'))
        for _ in range(2):
            response = self.client.post(detail_url(created['id'], 'activate/'))
            self.assertTrue(response.json()['active'])

    def test_unknown_id_returns_404(self):  # AC-08
        for suffix in ('activate/', 'deactivate/'):
            self.assertEqual(self.client.post(detail_url(uuid4(), suffix)).status_code, 404)


class DetailAndAccessTests(CustomerApiTestCase):
    def test_detail(self):  # AC-08
        created = self.create(name='Ana', phone='76543210', email='a@x.com', notes='n')
        self.assertEqual(self.client.get(detail_url(created['id'])).json(), created)

    def test_unknown_and_malformed_ids_return_404(self):  # AC-08
        response = self.client.get(detail_url(uuid4()))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'detail': 'Cliente no encontrado.'})
        self.assertEqual(self.client.get('/api/customers/no-es-uuid/').status_code, 404)

    def test_delete_and_put_are_not_allowed(self):  # AC-08, INV-05
        created = self.create(name='Ana')
        self.assertEqual(self.client.delete(detail_url(created['id'])).status_code, 405)
        self.assertEqual(self.client.put(detail_url(created['id']), {'name': 'x'}, format='json').status_code, 405)
        self.assertEqual(CustomerModel.objects.count(), 1)

    def test_all_endpoints_require_token(self):  # AC-08
        created = self.create(name='Ana')
        self.client.credentials()
        url = detail_url(created['id'])
        requests = (
            self.client.get(LIST_URL),
            self.client.post(LIST_URL, {'name': 'x'}, format='json'),
            self.client.get(url),
            self.client.patch(url, {'name': 'x'}, format='json'),
            self.client.post(url + 'activate/'),
            self.client.post(url + 'deactivate/'),
        )
        for response in requests:
            self.assertEqual(response.status_code, 401)
