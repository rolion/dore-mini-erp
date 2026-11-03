from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from modules.accounts.testing import authenticate, make_admin
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.personnel.infrastructure.django.models import ProfessionalModel, SpecialtyModel

PROFESSIONALS = '/api/professionals/'
SPECIALTIES = '/api/specialties/'


class PersonnelApiTests(TestCase):
    def setUp(self):
        self.admin = make_admin(username='personnel-admin')
        self.other = make_admin(username='other-company')
        self.client = APIClient()
        authenticate(self.client, self.admin)
        self.modules = DjangoCompanyModuleRepository(self.admin.company_id)
        self.modules.enabled_keys()
        self.modules.enable('personnel')

    def create(self, url=PROFESSIONALS, **values):
        result = self.client.post(url, {'name': 'Ana', **values}, format='json')
        self.assertEqual(result.status_code, 201, result.content)
        return result.json()

    def test_minimal_profile_and_partial_update(self):
        item = self.create()
        self.assertIsNone(item['user_id'])
        self.assertEqual(item['specialty_ids'], [])
        response = self.client.patch(f"{PROFESSIONALS}{item['id']}/", {'phone': ' 123 '}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Ana')
        self.assertEqual(response.json()['phone'], '123')

    def test_invalid_inputs_and_forged_authority(self):
        for body in ({}, {'name': ' '}, {'name': 'Ana', 'email': 'invalid'},
                     {'name': 'Ana', 'company_id': str(self.other.company_id)},
                     {'name': 'Ana', 'created_by': self.other.id}, {'name': 'Ana', 'active': False},
                     {'name': 'Ana', 'specialty_ids': ['invalid']}, {'name': 'Ana', 'user_id': -1}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post(PROFESSIONALS, body, format='json').status_code, 400)
        self.assertEqual(ProfessionalModel.objects.count(), 0)

    def test_foreign_user_and_specialty_rejected(self):
        foreign = SpecialtyModel.objects.create(company_id=self.other.company_id, name='Otra',
                                                created_by=self.other.id, updated_by=self.other.id)
        for values in ({'user_id': self.other.id}, {'specialty_ids': [str(foreign.id)]},
                       {'user_id': 999999}, {'specialty_ids': [str(uuid4())]}):
            response = self.client.post(PROFESSIONALS, {'name': 'Ana', **values}, format='json')
            self.assertEqual(response.status_code, 400)
        self.assertEqual(ProfessionalModel.objects.count(), 0)

    def test_specialty_associations_and_lifecycle(self):
        specialty = self.create(SPECIALTIES, name='Ortodoncia')
        item = self.create(specialty_ids=[specialty['id'], specialty['id']])
        self.assertEqual(item['specialty_ids'], [specialty['id']])
        self.assertEqual(item['specialties'][0]['name'], 'Ortodoncia')
        url = f"{SPECIALTIES}{specialty['id']}/"
        self.assertEqual(self.client.patch(url, {'name': 'Nueva'}, format='json').status_code, 200)
        self.assertFalse(self.client.post(url + 'deactivate/').json()['active'])
        self.assertEqual(self.client.get(f"{PROFESSIONALS}{item['id']}/").json()['specialty_ids'], [specialty['id']])
        self.assertTrue(self.client.post(url + 'activate/').json()['active'])
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_user_unique_even_inactive_and_unlink_releases_it(self):
        item = self.create(user_id=self.admin.id)
        other = self.create(name='B')
        self.client.post(f"{PROFESSIONALS}{item['id']}/deactivate/")
        duplicate = self.client.patch(f"{PROFESSIONALS}{other['id']}/", {'name': 'Changed', 'user_id': self.admin.id}, format='json')
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn('user_id', duplicate.json())
        self.assertEqual(ProfessionalModel.objects.get(id=other['id']).name, 'B')
        unlink = self.client.patch(f"{PROFESSIONALS}{item['id']}/", {'user_id': None}, format='json')
        self.assertEqual(unlink.status_code, 200)
        self.assertEqual(unlink.json()['created_by'], self.admin.id)
        self.assertEqual(self.client.patch(f"{PROFESSIONALS}{other['id']}/", {'user_id': self.admin.id}, format='json').status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.admin.role, 'admin')

    def test_authority_and_history_survive_user_changes(self):
        item = self.create(user_id=self.admin.id)
        second = make_admin(company=self.admin.company, username='second-admin')
        authenticate(self.client, second)
        response = self.client.post(f"{PROFESSIONALS}{item['id']}/deactivate/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['created_by'], self.admin.id)
        self.assertEqual(response.json()['updated_by'], second.id)
        self.assertEqual(response.json()['user_id'], self.admin.id)
        self.assertEqual(self.client.delete(f"{PROFESSIONALS}{item['id']}/").status_code, 405)

    def test_filters_and_server_pagination(self):
        specialty = self.create(SPECIALTIES)
        self.create(name='Ana', specialty_ids=[specialty['id']])
        second = self.create(name='Bea')
        self.client.post(f"{PROFESSIONALS}{second['id']}/deactivate/")
        for params in ({'search': 'an'}, {'active': 'true'}, {'specialty_id': specialty['id']}, {'active': 'false'}):
            response = self.client.get(PROFESSIONALS, params)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['count'], 1)
        page = self.client.get(PROFESSIONALS, {'page_size': 1, 'page': 2}).json()
        self.assertEqual(page['count'], 2)
        self.assertEqual(len(page['results']), 1)
        self.assertEqual(self.client.get(PROFESSIONALS, {'active': 'invalid'}).status_code, 400)
        self.assertEqual(self.client.get(PROFESSIONALS, {'specialty_id': 'invalid'}).status_code, 400)

    def test_foreign_and_unknown_object_urls(self):
        item = self.create()
        authenticate(self.client, self.other)
        DjangoCompanyModuleRepository(self.other.company_id).enable('personnel')
        for id_value in (item['id'], uuid4()):
            url = f'{PROFESSIONALS}{id_value}/'
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.patch(url, {'name': 'Hacked'}, format='json').status_code, 404)
            self.assertEqual(self.client.post(url + 'deactivate/').status_code, 404)
        self.assertEqual(self.client.get(PROFESSIONALS).json()['count'], 0)

    def test_user_selector_scoped_and_searchable(self):
        body = self.client.get(PROFESSIONALS + 'users/', {'search': 'personnel-admin'}).json()
        self.assertEqual(body['results'], [{'id': self.admin.id, 'name': ' (personnel-admin)'}])
        self.assertEqual(self.client.get(PROFESSIONALS + 'users/', {'id': self.other.id}).json()['count'], 0)
        self.assertEqual(self.client.get(PROFESSIONALS + 'users/', {'id': self.admin.id}).json()['count'], 1)
        self.assertEqual(self.client.get(PROFESSIONALS + 'users/', {'id': 'invalid'}).status_code, 400)

    def test_auth_permission_and_gate(self):
        for url in (PROFESSIONALS, SPECIALTIES, PROFESSIONALS + 'users/'):
            self.modules.disable('personnel')
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()['code'], 'module_disabled')
            self.modules.enable('personnel')
        self.admin.role = 'reception'
        self.admin.save()
        self.assertEqual(self.client.get(PROFESSIONALS).status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get(PROFESSIONALS).status_code, 401)

    def test_safe_http_methods(self):
        item = self.create()
        self.assertEqual(self.client.post(f"{PROFESSIONALS}{item['id']}/").status_code, 405)
        self.assertEqual(self.client.patch(PROFESSIONALS, {'name': 'x'}).status_code, 405)
        self.assertEqual(self.client.get(f"{PROFESSIONALS}{item['id']}/activate/").status_code, 405)


class UserLinkConcurrencyTests(TransactionTestCase):
    def test_only_one_concurrent_link_succeeds(self):
        self.assertEqual(connection.vendor, 'postgresql')
        user = make_admin(username='concurrent-professional')
        modules = DjangoCompanyModuleRepository(user.company_id)
        modules.enabled_keys()
        modules.enable('personnel')
        barrier = Barrier(2)

        def create(name):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(user)
                barrier.wait(timeout=10)
                return client.post(PROFESSIONALS, {'name': name, 'user_id': user.id}, format='json').status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(create, ['Ana', 'Bea']))
        self.assertEqual(sorted(results), [201, 400])
        self.assertEqual(ProfessionalModel.objects.filter(user_id=user.id).count(), 1)
