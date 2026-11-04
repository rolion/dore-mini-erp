from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest import mock
from uuid import uuid4

from django.apps import apps
from django.db import connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from modules.accounts.testing import make_admin
from modules.customers.infrastructure.django.models import CustomerModel
from modules.dentistry.infrastructure.models import PatientModel
from modules.dentistry.infrastructure.proforma_models import DentalProformaLineModel, DentalProformaModel
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.quotations.infrastructure.django.models import ProformaModel
from modules.service_catalog.infrastructure.django.models import ServiceModel

ROOT = '/api/dentistry/'


class DentalProformaApiTests(TransactionTestCase):
    def setUp(self):
        self.admin = make_admin(username='dental-admin')
        self.other = make_admin(username='dental-other')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.modules = DjangoCompanyModuleRepository(self.admin.company_id)
        self.modules.enabled_keys()
        for key in ('catalog', 'services', 'dentistry'):
            self.modules.enable(key)
        company = self.admin.company_id
        self.customer = CustomerModel.objects.create(company_id=company, name='Rosa Pérez')
        self.patient = PatientModel.objects.create(
            company_id=company, customer_id=self.customer.pk, created_by=self.admin.pk, updated_by=self.admin.pk)
        self.limpieza = ServiceModel.objects.create(
            company_id=company, name='Limpieza', base_price=Decimal('100.00'), duration_minutes=30)
        self.corona = ServiceModel.objects.create(
            company_id=company, name='Corona', base_price=Decimal('150.00'), duration_minutes=60)
        self.url = f'{ROOT}patients/{self.customer.pk}/proformas/'

    def payload(self, lines=None, **extra):
        lines = lines if lines is not None else [
            {'service_id': str(self.limpieza.pk), 'quantity': '1'},
            {'service_id': str(self.corona.pk), 'quantity': '1'}]
        return {'date': '2026-11-04', 'lines': lines, **extra}

    def create(self, **kwargs):
        return self.client.post(self.url, self.payload(**kwargs), format='json')

    def detail(self, proforma_id):
        return f'{ROOT}proformas/{proforma_id}/'

    # AC-01
    def test_total_number_and_snapshot_survive_catalog_changes(self):
        response = self.create(total='1', customer_id=str(uuid4()), lines=[
            {'service_id': str(self.limpieza.pk), 'quantity': '1', 'subtotal': '9'},
            {'service_id': str(self.corona.pk), 'quantity': '1'}])
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual((body['total'], body['number'], body['version'], body['status']),
                         ('250.00', 'ODO-000001', 1, 'draft'))
        self.assertEqual((body['customer_id'], body['patient_name']), (str(self.customer.pk), 'Rosa Pérez'))
        ServiceModel.objects.filter(pk=self.limpieza.pk).update(name='Otro', base_price=Decimal('999'), active=False)
        again = self.client.get(self.detail(body['id'])).json()
        self.assertEqual((again['total'], again['lines'][0]['description']), ('250.00', 'Limpieza'))
        updated = self.client.put(self.detail(body['id']), self.payload(lines=again['lines']), format='json')
        self.assertEqual((updated.status_code, updated.json()['total']), (200, '250.00'))

    # AC-02
    def test_dental_piece_is_optional_text_per_line_and_kept_in_new_versions(self):
        lines = [{'service_id': str(self.limpieza.pk), 'quantity': '1', 'dental_piece': ' 18 '},
                 {'service_id': str(self.corona.pk), 'quantity': '1'},
                 {'service_id': str(self.corona.pk), 'quantity': '1', 'dental_piece': '11-13'}]
        body = self.create(lines=lines).json()
        self.assertEqual([l['dental_piece'] for l in body['lines']], ['18', '', '11-13'])
        edited = [{**body['lines'][0]}, {**body['lines'][1], 'dental_piece': '36'}, {**body['lines'][2]}]
        edited[2].pop('dental_piece')  # no enviada: conserva la guardada
        saved = self.client.put(self.detail(body['id']), self.payload(lines=edited), format='json').json()
        self.assertEqual([l['dental_piece'] for l in saved['lines']], ['18', '36', '11-13'])
        self.client.post(self.detail(body['id']) + 'present/')
        draft = self.client.post(self.detail(body['id']) + 'new-version/').json()
        self.assertEqual([l['dental_piece'] for l in draft['lines']], ['18', '36', '11-13'])
        self.assertEqual(DentalProformaLineModel.objects.filter(dental_piece='36').count(), 2)

    def test_invalid_piece_is_a_400_on_that_line(self):  # AC-02
        for bad in ('x' * 21, '1\n2'):
            response = self.create(lines=[
                {'service_id': str(self.limpieza.pk), 'quantity': '1'},
                {'service_id': str(self.corona.pk), 'quantity': '1', 'dental_piece': bad}])
            self.assertEqual(response.status_code, 400, bad)
            self.assertEqual(response.json()['lines'][0], {})
            self.assertIn('dental_piece', response.json()['lines'][1])
        self.assertEqual(DentalProformaModel.objects.count(), 0)

    # AC-03
    def test_invalid_quantity_and_price_are_rejected_per_line(self):
        for quantity, price in (('0', None), ('-1', None), ('1', '-5')):
            line = {'service_id': str(self.limpieza.pk), 'quantity': quantity}
            if price is not None:
                line['unit_price'] = price
            response = self.create(lines=[{'service_id': str(self.corona.pk), 'quantity': '1'}, line])
            self.assertEqual(response.status_code, 400, (quantity, price))
            self.assertTrue(response.json()['lines'][1])
        self.assertEqual(DentalProformaModel.objects.count(), 0)

    # AC-04
    def test_price_override_requires_permission(self):
        line = {'service_id': str(self.limpieza.pk), 'quantity': '2', 'unit_price': '80.00'}
        ok = self.create(lines=[line])
        self.assertEqual((ok.status_code, ok.json()['total']), (201, '160.00'))
        with mock.patch('modules.dentistry.api.proforma_views.can_edit_price', return_value=False):
            self.assertEqual(self.create(lines=[line]).status_code, 403)
            same = self.create(lines=[{**line, 'unit_price': '100.00'}])
            self.assertEqual(same.status_code, 201)
            self.assertFalse(same.json()['can_edit_price'])
            frozen = ok.json()['lines'][0]
            denied = self.client.put(self.detail(ok.json()['id']), self.payload(lines=[
                {**frozen, 'unit_price': '10.00'}]), format='json')
            self.assertEqual(denied.status_code, 403)

    # AC-05
    def test_present_needs_lines_then_freezes_and_versions_supersede(self):
        empty = self.create(lines=[]).json()
        self.assertEqual(self.client.post(self.detail(empty['id']) + 'present/').status_code, 400)
        body = self.create().json()
        self.assertEqual(self.client.post(self.detail(body['id']) + 'new-version/').status_code, 409)
        presented = self.client.post(self.detail(body['id']) + 'present/')
        self.assertEqual((presented.status_code, presented.json()['status']), (200, 'presented'))
        self.assertEqual(self.client.put(self.detail(body['id']), self.payload(), format='json').status_code, 409)
        self.assertEqual(self.client.post(self.detail(body['id']) + 'present/').status_code, 409)
        ServiceModel.objects.filter(pk=self.limpieza.pk).update(base_price=Decimal('500'))
        draft = self.client.post(self.detail(body['id']) + 'new-version/')
        self.assertEqual((draft.status_code, draft.json()['version'], draft.json()['total']), (201, 2, '250.00'))
        self.assertEqual(self.client.post(self.detail(body['id']) + 'new-version/').status_code, 409)
        self.assertEqual(self.client.post(self.detail(draft.json()['id']) + 'present/').status_code, 200)
        first = self.client.get(self.detail(body['id'])).json()
        self.assertEqual([(v['version'], v['status']) for v in first['versions']],
                         [(1, 'superseded'), (2, 'presented')])

    # AC-06
    def test_patient_must_exist_be_active_and_customer_active(self):
        stranger = CustomerModel.objects.create(company_id=self.admin.company_id, name='Sin perfil')
        no_profile = self.client.post(f'{ROOT}patients/{stranger.pk}/proformas/', self.payload(), format='json')
        self.assertEqual(no_profile.status_code, 404)
        self.assertEqual(self.client.get(f'{ROOT}patients/{uuid4()}/proformas/').status_code, 404)
        foreign = CustomerModel.objects.create(company_id=self.other.company_id, name='Ajena')
        PatientModel.objects.create(company_id=self.other.company_id, customer_id=foreign.pk,
                                    created_by=self.other.pk, updated_by=self.other.pk)
        self.assertEqual(self.client.post(f'{ROOT}patients/{foreign.pk}/proformas/', self.payload(),
                                          format='json').status_code, 404)
        body = self.create().json()
        PatientModel.objects.filter(pk=self.patient.pk).update(active=False)
        self.assertEqual(self.create().status_code, 409)
        for call in (lambda: self.client.put(self.detail(body['id']), self.payload(lines=body['lines']), format='json'),
                     lambda: self.client.post(self.detail(body['id']) + 'present/')):
            self.assertEqual(call().status_code, 409)
        self.assertEqual(self.client.get(self.url).status_code, 200)  # la lista se conserva
        PatientModel.objects.filter(pk=self.patient.pk).update(active=True)
        CustomerModel.objects.filter(pk=self.customer.pk).update(active=False)
        inactive = self.create()
        self.assertEqual(inactive.status_code, 400)
        self.assertIn('customer_id', inactive.json())
        self.assertEqual(self.client.post(self.detail(body['id']) + 'present/').status_code, 400)

    # AC-07
    def test_patient_list_shows_only_that_patient_with_status_and_filter(self):
        first = self.create().json()
        self.client.post(self.detail(first['id']) + 'present/')
        self.create()
        second_customer = CustomerModel.objects.create(company_id=self.admin.company_id, name='Otro paciente')
        PatientModel.objects.create(company_id=self.admin.company_id, customer_id=second_customer.pk,
                                    created_by=self.admin.pk, updated_by=self.admin.pk)
        self.client.post(f'{ROOT}patients/{second_customer.pk}/proformas/', self.payload(), format='json')
        ProformaModel.objects.create(company_id=self.admin.company_id, number='PRO-000001',
                                     customer_id=self.customer.pk, customer_name='Rosa', date='2026-11-04')
        listing = self.client.get(self.url).json()
        self.assertEqual(listing['count'], 2)
        self.assertEqual({row['status'] for row in listing['results']}, {'draft', 'presented'})
        self.assertTrue(all(row['customer_id'] == str(self.customer.pk) for row in listing['results']))
        self.assertTrue(all(row['number'].startswith('ODO-') for row in listing['results']))
        self.assertEqual(self.client.get(self.url, {'status': 'presented'}).json()['count'], 1)
        self.assertEqual(self.client.get(self.url, {'status': 'x'}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {'page_size': '0'}).status_code, 400)
        foreign = DentalProformaModel.objects.create(
            company_id=self.other.company_id, number='ODO-000001', customer_id=uuid4(), patient_name='X',
            date='2026-11-04')
        self.assertEqual(self.client.get(self.detail(foreign.pk)).status_code, 404)
        self.assertEqual(self.client.post(self.detail(foreign.pk) + 'present/').status_code, 404)

    # AC-08
    def test_disabled_modules_return_403(self):
        for key in ('services', 'dentistry'):
            self.modules.disable(key)
            response = self.client.get(self.url)
            self.assertEqual((response.status_code, response.json()['code']), (403, 'module_disabled'), key)
            self.modules.enable(key)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    # AC-09
    def test_numbering_is_unique_under_concurrency_and_per_company(self):
        workers = 4
        barrier = Barrier(workers)

        def create_one(_):
            client = APIClient()
            client.force_authenticate(self.admin)
            barrier.wait()
            try:
                return client.post(self.url, self.payload(), format='json').json()['number']
            finally:
                connections.close_all()

        with ThreadPoolExecutor(workers) as pool:
            numbers = list(pool.map(create_one, range(workers)))
        self.assertEqual(sorted(numbers), [f'ODO-{n:06d}' for n in range(1, workers + 1)])
        other = DjangoCompanyModuleRepository(self.other.company_id)
        other.enabled_keys()
        for key in ('catalog', 'services', 'dentistry'):
            other.enable(key)
        customer = CustomerModel.objects.create(company_id=self.other.company_id, name='B')
        PatientModel.objects.create(company_id=self.other.company_id, customer_id=customer.pk,
                                    created_by=self.other.pk, updated_by=self.other.pk)
        service = ServiceModel.objects.create(company_id=self.other.company_id, name='S',
                                              base_price=Decimal('1'), duration_minutes=5)
        client = APIClient()
        client.force_authenticate(self.other)
        response = client.post(f'{ROOT}patients/{customer.pk}/proformas/', {'date': '2026-11-04', 'lines': [
            {'service_id': str(service.pk), 'quantity': '1'}]}, format='json')
        self.assertEqual(response.json()['number'], 'ODO-000001')

    # INV-07 / AC-11
    def test_no_sales_stock_or_generic_proformas_are_created(self):
        before = {model: model.objects.count() for app in ('sales', 'inventory', 'purchases', 'expenses', 'quotations')
                  for model in apps.get_app_config(app).get_models()}
        body = self.create().json()
        for _ in range(2):
            self.client.put(self.detail(body['id']), self.payload(lines=body['lines']), format='json')
        self.client.post(self.detail(body['id']) + 'present/')
        for model, count in before.items():
            self.assertEqual(model.objects.count(), count, model.__name__)
        self.assertEqual(DentalProformaModel.objects.count(), 1)
