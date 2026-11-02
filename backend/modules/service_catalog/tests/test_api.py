from dataclasses import FrozenInstanceError
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

from django.db import IntegrityError, connections, transaction
from django.test import TransactionTestCase
from rest_framework.test import APIClient, APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.modularity.infrastructure.django.models import CompanyModuleModel, CompanySettingsModel
from modules.service_catalog.infrastructure.django.models import ServiceModel
from modules.service_catalog.services import get_service, get_service_for_new_use

URL = '/api/services/'


class ServiceApiTests(APITestCase):
    def setUp(self):
        self.company = make_company('Servicios A')
        self.user = make_admin(self.company, username='service-admin')
        authenticate(self.client, self.user)
        CompanySettingsModel.objects.create(company_id=self.company.id)
        CompanyModuleModel.objects.create(company_id=self.company.id, module_key='services')

    def create(self, **values):
        response = self.client.post(URL, {'name': 'Consulta', 'base_price': '120',
                                         'duration_minutes': 30, **values}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_create_without_specialty_and_list_detail(self):
        body = self.create(code=' lim-01 ', company_id=str(uuid4()), active=False)
        self.assertEqual((body['code'], body['base_price'], body['duration_minutes']), ('LIM-01', '120.00', 30))
        self.assertTrue(body['active'])
        self.assertIsNone(body['specialty_id'])
        self.assertIsNone(body['specialty_name'])
        self.assertEqual(ServiceModel.objects.get(pk=body['id']).company_id, self.company.id)
        self.assertEqual(self.client.get(f"{URL}{body['id']}/").json(), body)
        self.assertEqual(self.client.get(URL).json()['results'], [body])

    def test_code_normalization_uniqueness_clear_and_reuse(self):
        first = self.create(code='lim-01')
        duplicate = self.client.post(URL, {'name': 'Otra', 'code': ' LiM-01 ', 'base_price': '1',
                                           'duration_minutes': 10}, format='json')
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn('code', duplicate.json())
        second = self.create(code='two')
        conflict = self.client.patch(f"{URL}{second['id']}/", {'code': 'lim-01'}, format='json')
        self.assertEqual(conflict.status_code, 400)
        self.assertEqual(self.client.get(f"{URL}{second['id']}/").json()['code'], 'TWO')
        cleared = self.client.patch(f"{URL}{first['id']}/", {'code': ''}, format='json')
        self.assertEqual(cleared.status_code, 200)
        self.create(code='lim-01')
        self.create(code='')
        self.create()

    def test_constraints_protect_direct_writes(self):
        body = self.create(code='UPPER')
        for changes in ({'code': 'lower'}, {'code': ' PAD '}, {'base_price': '-1'}, {'duration_minutes': 0}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                ServiceModel.objects.filter(pk=body['id']).update(**changes)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ServiceModel.objects.create(company_id=self.company.id, name='Duplicate', code='UPPER',
                                        base_price='0', duration_minutes=1)

    def test_invalid_required_fields_and_precision(self):
        response = self.client.post(URL, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'name', 'base_price', 'duration_minutes'})
        for field, value in [('duration_minutes', 0), ('duration_minutes', -1), ('duration_minutes', 1.5),
                             ('duration_minutes', True), ('base_price', '-1'), ('base_price', '1.001'),
                             ('base_price', 'NaN'), ('base_price', 'Infinity'), ('name', ' '),
                             ('base_price', '10000000000.00')]:
            with self.subTest(field=field, value=value):
                response = self.client.post(URL, {'name': 'Consulta', 'base_price': '120',
                                                  'duration_minutes': 30, field: value}, format='json')
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(field, response.json())
        self.assertEqual(ServiceModel.objects.count(), 0)
        self.create(base_price='0', duration_minutes=1)

    def test_update_snapshot_and_active_selector(self):
        body = self.create()
        service_id = body['id']
        before = get_service(self.company.id, service_id)
        response = self.client.patch(f'{URL}{service_id}/', {'base_price': '150', 'duration_minutes': 45}, format='json')
        self.assertEqual(response.status_code, 200)
        after = get_service_for_new_use(self.company.id, service_id)
        self.assertEqual((before.base_price, before.duration_minutes), (Decimal('120'), 30))
        self.assertEqual((after.base_price, after.duration_minutes), (Decimal('150'), 45))
        with self.assertRaises(FrozenInstanceError):
            before.duration_minutes = 45
        for _ in range(2):
            self.assertEqual(self.client.post(f'{URL}{service_id}/deactivate/').status_code, 200)
        self.assertEqual(self.client.get(URL, {'active': 'true'}).json()['count'], 0)
        self.assertEqual(self.client.get(URL, {'active': 'false'}).json()['count'], 1)
        self.assertIsNone(get_service_for_new_use(self.company.id, service_id))
        self.assertEqual(get_service(self.company.id, service_id).duration_minutes, 45)
        self.assertEqual(self.client.post(f'{URL}{service_id}/activate/').status_code, 200)
        self.assertIsNotNone(get_service_for_new_use(self.company.id, service_id))
        self.assertEqual(self.client.delete(f'{URL}{service_id}/').status_code, 405)

    def test_foreign_services_are_invisible_in_every_operation(self):
        foreign_company = make_company('Servicios B')
        foreign = ServiceModel.objects.create(company_id=foreign_company.id, name='Ajeno', code='SHARED',
                                               base_price='120', duration_minutes=30)
        self.assertEqual(self.client.get(URL).json()['count'], 0)
        for method, suffix in [('get', ''), ('patch', ''), ('post', 'activate/'), ('post', 'deactivate/')]:
            response = getattr(self.client, method)(f'{URL}{foreign.id}/{suffix}', {}, format='json')
            self.assertEqual(response.status_code, 404, response.content)
        self.assertIsNone(get_service(self.company.id, foreign.id))
        self.create(code='shared')
        foreign.refresh_from_db()
        self.assertTrue(foreign.active)

    def test_specialty_without_provider_is_optional_but_never_unvalidated(self):
        body = self.create(specialty_id=None)
        for specialty in [str(uuid4()), 'invalid']:
            response = self.client.patch(f"{URL}{body['id']}/", {'specialty_id': specialty}, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('specialty_id', response.json())
        self.assertEqual(self.client.get(URL, {'specialty_id': 'none'}).json()['count'], 1)
        self.assertEqual(self.client.get(URL, {'specialty_id': str(uuid4())}).json()['count'], 0)
        self.assertEqual(self.client.get(URL, {'specialty_id': 'invalid'}).status_code, 400)

    def test_search_pagination_and_invalid_filter(self):
        self.create(name='Evaluación')
        self.create(name='Limpieza')
        body = self.client.get(URL, {'search': 'limp', 'page_size': 1}).json()
        self.assertEqual(body['count'], 1)
        self.assertEqual(body['results'][0]['name'], 'Limpieza')
        self.assertEqual(self.client.get(URL, {'active': 'oops'}).status_code, 400)

    def test_pagination_parameters_and_vanished_pages_are_field_errors(self):
        self.create()
        for field, raw in [('page', '0'), ('page', '-1'), ('page', 'abc'), ('page', '2'),
                           ('page_size', '0'), ('page_size', 'abc'), ('page_size', '1.5')]:
            with self.subTest(field=field, raw=raw):
                response = self.client.get(URL, {field: raw})
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(field, response.json())

    def test_disabled_module_and_unauthenticated_have_no_access(self):
        body = self.create()
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='services').delete()
        for method, suffix in [('get', ''), ('post', ''), ('get', f"{body['id']}/"),
                               ('patch', f"{body['id']}/"), ('post', f"{body['id']}/deactivate/")]:
            response = getattr(self.client, method)(f'{URL}{suffix}', {}, format='json')
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()['code'], 'module_disabled')
        self.assertIsNone(get_service(self.company.id, body['id']))
        self.client.force_authenticate(user=None)
        self.client.credentials()
        self.assertIn(self.client.get(URL).status_code, (401, 403))

    def test_inactive_company_and_non_admin_cannot_access(self):
        self.company.is_active = False
        self.company.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.company.is_active = True
        self.company.save(update_fields=['is_active'])
        self.user.role = 'unprivileged'
        self.user.save(update_fields=['role'])
        self.assertEqual(self.client.get(URL).status_code, 403)


class ConcurrentServiceCodeTests(TransactionTestCase):
    def test_concurrent_normalized_duplicates_return_one_created_and_one_field_error(self):
        company = make_company('Concurrent services')
        user = make_admin(company, username='concurrent-services')
        CompanySettingsModel.objects.create(company_id=company.id)
        CompanyModuleModel.objects.create(company_id=company.id, module_key='services')
        start = Barrier(2)

        def create(code):
            client = APIClient()
            client.force_authenticate(user=user)
            try:
                start.wait(timeout=10)
                response = client.post(URL, {'name': 'Consulta', 'base_price': '120',
                                            'duration_minutes': 30, 'code': code}, format='json')
                return response.status_code, response.json()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(create, ['con-01', 'CON-01']))
        self.assertEqual(sorted(status for status, _ in results), [201, 400])
        self.assertIn('code', next(body for status, body in results if status == 400))
        self.assertEqual(ServiceModel.objects.filter(company_id=company.id, code='CON-01').count(), 1)
