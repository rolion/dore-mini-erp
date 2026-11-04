from decimal import Decimal
from unittest import mock
from uuid import UUID, uuid4

from django.apps import apps
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from modules.accounts.testing import make_admin
from modules.customers.infrastructure.django.models import CustomerModel
from modules.dentistry.infrastructure.models import PatientModel
from modules.dentistry.infrastructure.proforma_models import (
    DentalProformaDecisionBatchModel, DentalProformaLineDecisionModel, DentalProformaLineModel,
)
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.service_catalog.infrastructure.django.models import ServiceModel

ROOT = '/api/dentistry/'


class DentalProformaDecisionApiTests(TransactionTestCase):
    def setUp(self):
        self.admin = make_admin(username='dental-dec-admin')
        self.other = make_admin(username='dental-dec-other')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.modules = DjangoCompanyModuleRepository(self.admin.company_id)
        self.modules.enabled_keys()
        for key in ('catalog', 'services', 'dentistry'):
            self.modules.enable(key)
        company = self.admin.company_id
        self.customer = CustomerModel.objects.create(company_id=company, name='Rosa Pérez')
        PatientModel.objects.create(company_id=company, customer_id=self.customer.pk, created_by=self.admin.pk,
                                    updated_by=self.admin.pk)
        self.a = ServiceModel.objects.create(company_id=company, name='Limpieza', base_price=Decimal('100.00'),
                                             duration_minutes=30)
        self.b = ServiceModel.objects.create(company_id=company, name='Corona', base_price=Decimal('200.00'),
                                             duration_minutes=60)
        self.url = f'{ROOT}patients/{self.customer.pk}/proformas/'

    def detail(self, proforma_id):
        return f'{ROOT}proformas/{proforma_id}/'

    def presented(self):
        body = self.client.post(self.url, {'date': '2026-11-04', 'lines': [
            {'service_id': str(self.a.pk), 'quantity': '1', 'dental_piece': '18'},
            {'service_id': str(self.b.pk), 'quantity': '1'}]}, format='json').json()
        return self.client.post(self.detail(body['id']) + 'present/').json()

    def decide(self, proforma, indexes, decision='accepted', key=None, **extra):
        data = {'idempotency_key': str(key or uuid4()), 'decision': decision,
                'line_ids': [proforma['lines'][i]['id'] for i in indexes]}
        if decision == 'accepted':
            data.update({'accepted_by_name': 'Rosa Pérez', 'medium': 'in_person'})
        return self.client.post(self.detail(proforma['id']) + 'decisions/', {**data, **extra}, format='json')

    def get(self, proforma):
        return self.client.get(self.detail(proforma['id'])).json()

    def test_accept_first_reject_second(self):  # AC-01
        p = self.presented()
        self.assertEqual(self.decide(p, [0], reference='Firma en consulta').status_code, 201)
        self.assertEqual(self.decide(p, [1], 'rejected', reason='Muy caro').status_code, 201)
        body = self.get(p)
        self.assertEqual(body['totals'], {'proposed': '300.00', 'accepted': '100.00', 'pending': '0.00',
                                          'rejected': '200.00'})
        self.assertEqual(body['acceptance_status'], 'partially_accepted')
        self.assertEqual([(l['decision'], l['authorized']) for l in body['lines']],
                         [('accepted', True), ('rejected', False)])
        self.assertEqual(body['lines'][0]['dental_piece'], '18')

    def test_batch_is_atomic_and_retry_is_idempotent(self):  # AC-02, AC-03
        p = self.presented()
        key = uuid4()
        self.assertEqual(self.decide(p, [0], key=key).status_code, 201)
        retry = self.decide(p, [0], key=key)
        self.assertEqual((retry.status_code, retry.json()['replayed']), (200, True))
        self.assertEqual(DentalProformaLineDecisionModel.objects.filter(kind='decision').count(), 1)
        self.assertEqual(self.decide(p, [1], key=key).status_code, 409)
        self.assertEqual(self.decide(p, [0]).status_code, 409)
        self.assertEqual(self.decide(p, [0, 1], 'rejected').status_code, 409)
        self.assertEqual([l['decision'] for l in self.get(p)['lines']], ['accepted', 'pending'])
        self.assertEqual(DentalProformaDecisionBatchModel.objects.count(), 1)

    def test_only_presented_accepts_decisions_and_fields_are_validated(self):  # AC-04, AC-05
        draft = self.client.post(self.url, {'date': '2026-11-04', 'lines': [
            {'service_id': str(self.a.pk), 'quantity': '1'}]}, format='json').json()
        self.assertEqual(self.decide(draft, [0]).status_code, 409)
        p = self.presented()
        for extra in ({'accepted_by_name': ''}, {'medium': 'paloma'}, {'medium': ''}):
            self.assertEqual(self.decide(p, [0], **extra).status_code, 400, extra)
        self.assertEqual(self.decide(p, []).status_code, 400)
        self.assertEqual(DentalProformaLineDecisionModel.objects.count(), 0)

    def test_rectification(self):  # AC-06
        p = self.presented()
        self.decide(p, [0])
        url = self.detail(p['id']) + f"lines/{p['lines'][0]['id']}/rectify/"
        self.assertEqual(self.client.post(url, {'idempotency_key': str(uuid4()), 'decision': 'rejected'},
                                          format='json').status_code, 400)
        with mock.patch('modules.dentistry.api.proforma_views.can_rectify', return_value=False):
            denied = self.client.post(url, {'idempotency_key': str(uuid4()), 'decision': 'rejected',
                                            'reason': 'x'}, format='json')
            self.assertEqual(denied.status_code, 403)
        ok = self.client.post(url, {'idempotency_key': str(uuid4()), 'decision': 'rejected',
                                    'reason': 'Se arrepintió'}, format='json')
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual([h['kind'] for h in self.get(p)['decision_history']], ['decision', 'rectification'])

    def test_new_version_keeps_piece_and_decisions_without_duplicating(self):  # AC-08, AC-09, AC-12
        p = self.presented()
        self.decide(p, [0])
        self.decide(p, [1], 'rejected')
        v2 = self.client.post(self.detail(p['id']) + 'new-version/').json()
        self.assertEqual([(l['line_kind'], l['decision'], l['dental_piece']) for l in v2['lines']],
                         [('carried', 'accepted', '18'), ('carried', 'rejected', '')])
        self.assertEqual(v2['totals']['accepted'], '100.00')
        removed = self.client.put(self.detail(v2['id']), {'date': '2026-11-04', 'lines': [v2['lines'][1]]},
                                  format='json')
        self.assertEqual(removed.status_code, 409)
        saved = self.client.put(self.detail(v2['id']), {'date': '2026-11-04', 'lines': [
            v2['lines'][0], {**v2['lines'][1], 'unit_price': '150.00'},
            {'service_id': str(self.a.pk), 'quantity': '1'}]}, format='json')
        self.assertEqual(saved.status_code, 200, saved.content)
        lines = saved.json()['lines']
        self.assertEqual([(l['line_kind'], l['decision']) for l in lines],
                         [('carried', 'accepted'), ('replacement', 'pending'), ('additional', 'pending')])
        self.assertEqual(lines[0]['id'], v2['lines'][0]['id'])
        self.client.post(self.detail(v2['id']) + 'present/')
        old = self.get(p)
        self.assertEqual((old['status'], old['totals']['accepted'], old['decision_actions']),
                         ('superseded', '100.00', []))
        self.assertEqual(DentalProformaLineModel.objects.filter(proforma_id=p['id']).count(), 2)

    def test_printable_exposes_only_commercial_data(self):  # AC-10
        p = self.presented()
        self.decide(p, [0], reference='SECRETO-REF')
        self.decide(p, [1], 'rejected', reason='SECRETO-MOTIVO')
        response = self.client.get(self.detail(p['id']) + 'printable/')
        self.assertEqual(response.status_code, 200)
        text = response.content.decode()
        for forbidden in ('SECRETO-REF', 'SECRETO-MOTIVO', 'dental-dec-admin', 'recorded_by', 'decision_history',
                          'origin_line_id', p['lines'][0]['id'], 'reference'):
            self.assertNotIn(forbidden, text)
        body = response.json()
        self.assertEqual(body['totals'], {'proposed': '300.00', 'accepted': '100.00', 'pending': '0.00'})
        self.assertEqual(body['lines'][0]['dental_piece'], '18')
        draft = self.client.post(self.url, {'date': '2026-11-04', 'lines': []}, format='json').json()
        self.assertEqual(self.client.get(self.detail(draft['id']) + 'printable/').status_code, 409)

    def test_isolation_modules_and_clinical_permission(self):  # AC-11
        p = self.presented()
        body = {'idempotency_key': str(uuid4()), 'decision': 'rejected', 'line_ids': [p['lines'][0]['id']]}
        stranger = APIClient()
        stranger.force_authenticate(self.other)
        self.assertEqual(stranger.post(self.detail(p['id']) + 'decisions/', body, format='json').status_code, 403)
        modules = DjangoCompanyModuleRepository(self.other.company_id)
        modules.enabled_keys()
        for key in ('catalog', 'services', 'dentistry'):
            modules.enable(key)
        self.assertEqual(stranger.post(self.detail(p['id']) + 'decisions/', body, format='json').status_code, 404)
        self.assertEqual(stranger.get(self.detail(p['id']) + 'printable/').status_code, 404)
        self.assertEqual(DentalProformaLineDecisionModel.objects.count(), 0)
        self.modules.disable('services')
        response = self.client.post(self.detail(p['id']) + 'decisions/', body, format='json')
        self.assertEqual((response.status_code, response.json()['code']), (403, 'module_disabled'))

    def test_saving_a_draft_keeps_line_ids_and_deciding_creates_no_sale_or_stock(self):  # AC-12, AC-13
        draft = self.client.post(self.url, {'date': '2026-11-04', 'lines': [
            {'service_id': str(self.a.pk), 'quantity': '1'}]}, format='json').json()
        self.client.put(self.detail(draft['id']), {'date': '2026-11-04', 'lines': draft['lines']}, format='json')
        self.assertEqual(list(DentalProformaLineModel.objects.values_list('id', flat=True)),
                         [UUID(draft['lines'][0]['id'])])
        before = {model: model.objects.count() for app in ('sales', 'inventory', 'purchases', 'expenses')
                  for model in apps.get_app_config(app).get_models()}
        p = self.presented()
        self.decide(p, [0])
        for model, count in before.items():
            self.assertEqual(model.objects.count(), count, model.__name__)
