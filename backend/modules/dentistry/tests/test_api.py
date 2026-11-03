from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4
from django.db import close_old_connections
from django.test import TransactionTestCase
from rest_framework.test import APITestCase, APIClient
from modules.accounts.testing import make_admin, make_company, authenticate
from modules.customers.infrastructure.django.models import CustomerModel
from modules.dentistry.infrastructure.models import PatientModel, PatientHistoryModel

ROOT = '/api/dentistry/'
LIST = ROOT + 'patients/'


def enable(client):
    response = client.post('/api/modules/dentistry/enable/', {}, format='json')
    assert response.status_code == 200, response.content


class PatientApiTests(APITestCase):
    def setUp(self):
        self.company = make_company()
        self.user = make_admin(self.company)
        authenticate(self.client, self.user)
        enable(self.client)
        self.customer = CustomerModel.objects.create(company_id=self.company.id, name='Ana', phone='+59176543210')
        self.detail = f'{LIST}{self.customer.id}/'

    def create(self, **extra):
        return self.client.post(LIST, {'customer_id': str(self.customer.id), **extra}, format='json')

    def test_create_conserves_identity_and_duplicate_is_conflict(self):
        response = self.create(allergies='Penicilina')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['id'], str(self.customer.id))
        self.assertEqual(response.json()['allergies'], 'Penicilina')
        self.assertEqual(self.create().status_code, 409)
        self.assertEqual(CustomerModel.objects.count(), 1)
        self.assertEqual(PatientModel.objects.count(), 1)
        self.assertEqual(PatientHistoryModel.objects.count(), 1)

    def test_list_search_pagination_has_only_administrative_data(self):
        self.create(clinical_notes='SECRETO')
        page = self.client.get(LIST, {'search': '76543210', 'page_size': 1}).json()
        self.assertEqual(page['count'], 1)
        self.assertNotIn('clinical_notes', page['results'][0])
        self.assertEqual(self.client.get(LIST, {'search': 'ninguno'}).json()['count'], 0)
        self.assertEqual(self.client.get(LIST, {'active': 'invalid'}).status_code, 400)

    def test_edit_trim_clear_audit_noop_and_actor_not_spoofable(self):
        self.create()
        updated = self.client.patch(self.detail, {'allergies': ' Asma ', 'updated_by': 999}, format='json')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['allergies'], 'Asma')
        self.assertEqual(updated.json()['updated_by'], self.user.id)
        self.client.patch(self.detail, {'allergies': 'Asma'}, format='json')
        self.assertEqual(PatientHistoryModel.objects.count(), 2)
        self.client.patch(self.detail, {'allergies': ''}, format='json')
        history = self.client.get(self.detail + 'history/').json()['results']
        self.assertEqual(history[0]['before']['allergies'], 'Asma')
        self.assertEqual(history[0]['after']['allergies'], '')
        self.assertEqual(history[0]['author_name'], self.user.username)

    def test_archive_conserves_history_identity_and_customer(self):
        self.create(medical_history='Antecedente')
        self.assertEqual(self.client.post(self.detail + 'archive/').status_code, 200)
        self.assertEqual(self.client.patch(self.detail, {'medical_history': ''}, format='json').status_code, 409)
        self.assertEqual(self.create().status_code, 409)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.active)
        self.assertEqual(self.client.get(LIST).json()['count'], 0)
        self.assertEqual(self.client.get(LIST, {'active': 'false'}).json()['count'], 1)
        response = self.client.post(self.detail + 'activate/')
        self.assertEqual(response.json()['id'], str(self.customer.id))
        self.assertEqual(response.json()['medical_history'], 'Antecedente')
        self.assertEqual(PatientHistoryModel.objects.count(), 3)

    def test_foreign_and_missing_customer_cannot_create_or_read_history(self):
        foreign = CustomerModel.objects.create(company_id=uuid4(), name='Otro')
        for customer_id in (foreign.id, uuid4()):
            self.assertEqual(self.client.post(LIST, {'customer_id': str(customer_id)}, format='json').status_code, 404)
        self.create()
        other = make_admin(make_company('Otra'), username='otra')
        other_client = APIClient()
        authenticate(other_client, other)
        enable(other_client)
        for suffix in ('', 'history/'):
            self.assertEqual(other_client.get(self.detail + suffix).status_code, 404)
        self.assertEqual(other_client.get(LIST).json()['count'], 0)
        self.assertEqual(other_client.patch(self.detail, {'allergies': 'no'}, format='json').status_code, 404)

    def test_company_id_in_payload_never_changes_owner(self):
        self.assertEqual(self.create(company_id=str(uuid4())).status_code, 201)
        self.assertEqual(PatientModel.objects.get().company_id, self.company.id)

    def test_clinical_policy_is_checked_even_for_admin(self):
        self.create()
        with patch('config.permissions.has_clinical_access', return_value=False):
            for url in (LIST, self.detail, self.detail + 'history/', ROOT + 'capabilities/'):
                self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.patch(self.detail, {}, format='json').status_code, 403)
            self.assertEqual(self.client.post(self.detail + 'archive/').status_code, 403)

    def test_module_disabled_blocks_all_clinical_endpoints(self):
        self.create()
        self.client.post('/api/modules/dentistry/disable/')
        for url in (LIST, self.detail, self.detail + 'history/', ROOT + 'capabilities/'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()['code'], 'module_disabled')

    def test_non_admin_inactive_missing_company_and_unauthenticated_denied(self):
        self.create()
        for role, company in (('reception', self.company), ('professional', self.company), ('admin', None)):
            self.user.role = role
            self.user.company = company
            self.user.save()
            self.assertEqual(self.client.get(self.detail).status_code, 403)
        self.user.company = self.company
        self.user.save()
        self.company.is_active = False
        self.company.save()
        self.assertEqual(self.client.get(self.detail).status_code, 403)
        self.client.credentials()
        self.assertIn(self.client.get(self.detail).status_code, (401, 403))

    def test_atomic_creation_and_edit_if_audit_fails(self):
        with patch.object(PatientHistoryModel.objects, 'create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.create()
        self.assertFalse(PatientModel.objects.exists())
        self.create()
        with patch.object(PatientHistoryModel.objects, 'create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.patch(self.detail, {'allergies': 'nuevo'}, format='json')
        self.assertEqual(PatientModel.objects.get().allergies, '')

    def test_invalid_input_and_read_only_history(self):
        self.assertEqual(self.create(allergies='a' * 4001).status_code, 400)
        self.assertEqual(self.client.post(LIST, {}, format='json').status_code, 400)
        self.create()
        self.assertEqual(self.client.post(self.detail + 'history/', {}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(self.detail).status_code, 405)
        self.assertTrue(self.client.get(ROOT + 'capabilities/').json()['clinical_access'])


class ConcurrentCreationTests(TransactionTestCase):
    def test_two_concurrent_creates_make_one_profile_and_one_audit(self):
        company = make_company()
        user = make_admin(company)
        client = APIClient()
        token = authenticate(client, user)
        enable(client)
        customer = CustomerModel.objects.create(company_id=company.id, name='Concurrente')
        barrier = Barrier(2)

        def create():
            close_old_connections()
            try:
                worker = APIClient()
                worker.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
                barrier.wait(timeout=10)
                return worker.post(LIST, {'customer_id': str(customer.id)}, format='json').status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: create(), range(2)))
        self.assertEqual(sorted(results), [201, 409])
        self.assertEqual(PatientModel.objects.count(), 1)
        self.assertEqual(PatientHistoryModel.objects.count(), 1)
