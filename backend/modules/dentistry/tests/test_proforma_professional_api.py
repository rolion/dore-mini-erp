from decimal import Decimal
from uuid import uuid4

from django.test import TransactionTestCase
from rest_framework.test import APIClient

from modules.accounts.testing import make_admin
from modules.customers.infrastructure.django.models import CustomerModel
from modules.dentistry.infrastructure.models import PatientModel
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.personnel.infrastructure.django.models import ProfessionalModel
from modules.service_catalog.infrastructure.django.models import ServiceModel

ROOT = '/api/dentistry/'


class ProformaProfessionalApiTests(TransactionTestCase):
    """AC-01 y AC-02: doctor opcional de la proforma."""

    def setUp(self):
        self.admin = make_admin(username='doc-admin')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        modules = DjangoCompanyModuleRepository(self.admin.company_id)
        modules.enabled_keys()
        for key in ('catalog', 'services', 'dentistry'):
            modules.enable(key)
        company = self.admin.company_id
        customer = CustomerModel.objects.create(company_id=company, name='Rosa Pérez')
        PatientModel.objects.create(company_id=company, customer_id=customer.pk, created_by=self.admin.pk,
                                    updated_by=self.admin.pk)
        self.service = ServiceModel.objects.create(company_id=company, name='Corona', base_price=Decimal('100.00'),
                                                   duration_minutes=60)
        self.doctor = ProfessionalModel.objects.create(company_id=company, name='Dra. Paz', created_by=1, updated_by=1)
        self.url = f'{ROOT}patients/{customer.pk}/proformas/'

    def body(self, **extra):
        return {'date': '2026-11-04', 'lines': [{'service_id': str(self.service.pk), 'quantity': '1'}], **extra}

    def test_doctor_is_optional_and_returned_in_detail_and_list(self):
        none = self.client.post(self.url, self.body(), format='json').json()
        self.assertIsNone(none['professional'])
        created = self.client.post(self.url, self.body(professional_id=str(self.doctor.pk)), format='json').json()
        self.assertEqual(created['professional'], {'id': str(self.doctor.pk), 'name': 'Dra. Paz'})
        listed = {p['id']: p for p in self.client.get(self.url).json()['results']}
        self.assertEqual(listed[created['id']]['professional']['name'], 'Dra. Paz')
        self.assertIsNone(listed[none['id']]['professional'])

    def test_doctor_of_another_company_or_unknown_is_a_400(self):
        foreign = ProfessionalModel.objects.create(company_id=uuid4(), name='Ajeno', created_by=1, updated_by=1)
        for bad in (str(foreign.pk), str(uuid4())):
            response = self.client.post(self.url, self.body(professional_id=bad), format='json')
            self.assertEqual(response.status_code, 400, response.content)
            self.assertIn('professional_id', response.json())
        draft = self.client.post(self.url, self.body(), format='json').json()
        put = self.client.put(f"{ROOT}proformas/{draft['id']}/", self.body(professional_id=str(foreign.pk)),
                              format='json')
        self.assertEqual(put.status_code, 400)

    def test_doctor_can_change_in_draft_and_new_version_inherits_it(self):
        draft = self.client.post(self.url, self.body(), format='json').json()
        saved = self.client.put(f"{ROOT}proformas/{draft['id']}/", self.body(professional_id=str(self.doctor.pk)),
                                format='json').json()
        self.assertEqual(saved['professional']['name'], 'Dra. Paz')
        self.client.post(f"{ROOT}proformas/{draft['id']}/present/")
        version = self.client.post(f"{ROOT}proformas/{draft['id']}/new-version/").json()
        self.assertEqual((version['version'], version['professional']['id']), (2, str(self.doctor.pk)))
