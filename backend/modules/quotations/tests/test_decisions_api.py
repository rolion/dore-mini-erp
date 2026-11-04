from decimal import Decimal
from unittest import mock
from uuid import UUID, uuid4

from django.apps import apps
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from modules.accounts.testing import make_admin
from modules.customers.infrastructure.django.models import CustomerModel
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.quotations.infrastructure.django.models import (
    ProformaDecisionBatchModel, ProformaLineDecisionModel, ProformaLineModel, ProformaModel,
)
from modules.service_catalog.infrastructure.django.models import ServiceModel

URL = '/api/quotations/proformas/'


class ProformaDecisionApiTests(TransactionTestCase):
    def setUp(self):
        self.admin = make_admin(username='dec-admin')
        self.other = make_admin(username='dec-other')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        modules = DjangoCompanyModuleRepository(self.admin.company_id)
        modules.enabled_keys()
        for key in ('catalog', 'services', 'quotations'):
            modules.enable(key)
        company = self.admin.company_id
        self.customer = CustomerModel.objects.create(company_id=company, name='Rosa Pérez')
        self.a = ServiceModel.objects.create(company_id=company, name='Limpieza', base_price=Decimal('100.00'),
                                             duration_minutes=30)
        self.b = ServiceModel.objects.create(company_id=company, name='Corona', base_price=Decimal('200.00'),
                                             duration_minutes=60)

    def presented(self):
        body = self.client.post(URL, {'customer_id': str(self.customer.pk), 'date': '2026-11-03', 'lines': [
            {'service_id': str(self.a.pk), 'quantity': '1'}, {'service_id': str(self.b.pk), 'quantity': '1'}]},
            format='json').json()
        return self.client.post(f"{URL}{body['id']}/present/").json()

    def decide(self, proforma, indexes, decision='accepted', key=None, **extra):
        data = {'idempotency_key': str(key or uuid4()), 'decision': decision,
                'line_ids': [proforma['lines'][i]['id'] for i in indexes]}
        if decision == 'accepted':
            data.update({'accepted_by_name': 'Rosa Pérez', 'medium': 'in_person'})
        return self.client.post(f"{URL}{proforma['id']}/decisions/", {**data, **extra}, format='json')

    def get(self, proforma):
        return self.client.get(f"{URL}{proforma['id']}/").json()

    # AC-01
    def test_accept_first_reject_second(self):
        p = self.presented()
        first = self.decide(p, [0], reference='WhatsApp 12:30')
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(first.json()['summary'], {'lines': 1, 'amount': '100.00'})
        second = self.decide(p, [1], 'rejected', reason='Muy caro')
        self.assertEqual(second.status_code, 201, second.content)
        body = self.get(p)
        self.assertEqual(body['totals'], {'proposed': '300.00', 'accepted': '100.00', 'pending': '0.00',
                                          'rejected': '200.00'})
        self.assertEqual(body['acceptance_status'], 'partially_accepted')
        self.assertEqual([(l['decision'], l['authorized']) for l in body['lines']],
                         [('accepted', True), ('rejected', False)])
        self.assertEqual(body['lines'][0]['decision_detail']['recorded_by_name'], 'dec-admin')
        self.assertEqual(len(body['decision_history']), 2)

    # AC-02
    def test_batch_is_atomic(self):
        p = self.presented()
        self.assertEqual(self.decide(p, [0]).status_code, 201)
        response = self.decide(p, [0, 1], 'rejected')
        self.assertEqual(response.status_code, 409)
        self.assertEqual([l['decision'] for l in self.get(p)['lines']], ['accepted', 'pending'])
        both = self.decide(self.presented(), [0, 1])
        self.assertEqual(both.json()['summary'], {'lines': 2, 'amount': '300.00'})

    # AC-03
    def test_retry_with_same_key_is_idempotent(self):
        p = self.presented()
        key = uuid4()
        self.assertEqual(self.decide(p, [0], key=key).status_code, 201)
        retry = self.decide(p, [0], key=key)
        self.assertEqual((retry.status_code, retry.json()['replayed']), (200, True))
        self.assertEqual(ProformaLineDecisionModel.objects.filter(kind='decision').count(), 1)
        self.assertEqual(self.get(p)['totals']['accepted'], '100.00')
        self.assertEqual(self.decide(p, [1], key=key).status_code, 409)  # misma clave, otras líneas
        self.assertEqual(self.decide(p, [0]).status_code, 409)  # otra clave, línea ya decidida
        self.assertEqual(ProformaDecisionBatchModel.objects.count(), 1)

    # AC-04
    def test_only_presented_proformas_accept_decisions(self):
        draft = self.client.post(URL, {'customer_id': str(self.customer.pk), 'date': '2026-11-03', 'lines': [
            {'service_id': str(self.a.pk), 'quantity': '1'}]}, format='json').json()
        self.assertEqual(self.decide(draft, [0]).status_code, 409)
        p = self.presented()
        self.assertEqual([l['decision'] for l in p['lines']], ['pending', 'pending'])  # presentar no acepta
        v2 = self.client.post(f"{URL}{p['id']}/new-version/").json()
        self.client.post(f"{URL}{v2['id']}/present/")
        self.assertEqual(self.decide(p, [0]).status_code, 409)  # v1 ya está reemplazada

    # AC-05
    def test_field_validation_and_foreign_lines(self):
        p = self.presented()
        for extra in ({'accepted_by_name': ''}, {'medium': 'paloma'}, {'medium': ''}, {'reference': 'x' * 201}):
            response = self.decide(p, [0], **extra)
            self.assertEqual(response.status_code, 400, extra)
        self.assertEqual(self.decide(p, []).status_code, 400)
        foreign = {'idempotency_key': str(uuid4()), 'decision': 'rejected', 'line_ids': [str(uuid4())]}
        self.assertEqual(self.client.post(f"{URL}{p['id']}/decisions/", foreign, format='json').status_code, 400)
        self.assertEqual(ProformaLineDecisionModel.objects.count(), 0)

    # AC-06
    def test_rectification_requires_reason_and_permission_and_keeps_history(self):
        p = self.presented()
        self.decide(p, [0])
        line = p['lines'][0]['id']
        url = f"{URL}{p['id']}/lines/{line}/rectify/"
        no_reason = self.client.post(url, {'idempotency_key': str(uuid4()), 'decision': 'rejected'}, format='json')
        self.assertEqual(no_reason.status_code, 400)
        with mock.patch('modules.quotations.api.views.can_rectify', return_value=False):
            denied = self.client.post(url, {'idempotency_key': str(uuid4()), 'decision': 'rejected',
                                            'reason': 'x'}, format='json')
            self.assertEqual(denied.status_code, 403)
            self.assertNotIn('rectify', self.get(p)['decision_actions'])
        ok = self.client.post(url, {'idempotency_key': str(uuid4()), 'decision': 'rejected',
                                    'reason': 'Se arrepintió'}, format='json')
        self.assertEqual(ok.status_code, 201, ok.content)
        body = self.get(p)
        self.assertEqual((body['lines'][0]['decision'], body['totals']['accepted']), ('rejected', '0.00'))
        self.assertEqual([h['kind'] for h in body['decision_history']], ['decision', 'rectification'])
        pending = f"{URL}{p['id']}/lines/{p['lines'][1]['id']}/rectify/"
        self.assertEqual(self.client.post(pending, {'idempotency_key': str(uuid4()), 'decision': 'rejected',
                                                    'reason': 'x'}, format='json').status_code, 409)

    # AC-08 / AC-09
    def test_new_version_carries_decisions_without_duplicating_commitments(self):
        p = self.presented()
        self.decide(p, [0])
        self.decide(p, [1], 'rejected')
        v2 = self.client.post(f"{URL}{p['id']}/new-version/").json()
        self.assertEqual([(l['line_kind'], l['decision']) for l in v2['lines']],
                         [('carried', 'accepted'), ('carried', 'rejected')])
        self.assertEqual([l['origin_line_id'] for l in v2['lines']], [l['id'] for l in p['lines']])
        self.assertEqual(v2['totals']['accepted'], '100.00')
        self.assertEqual(v2['previous_version_id'], p['id'])
        # editar la aceptada o quitarla → 409; editar la rechazada → reemplazo pendiente
        header = {'customer_id': str(self.customer.pk), 'date': '2026-11-03'}
        keep = [{'id': v2['lines'][0]['id'], 'quantity': '1.00'}]
        edit_accepted = self.client.put(f"{URL}{v2['id']}/", {**header, 'lines': [
            {'id': v2['lines'][0]['id'], 'quantity': '2.00'}, {'id': v2['lines'][1]['id'], 'quantity': '1.00'}]},
            format='json')
        self.assertEqual(edit_accepted.status_code, 409)
        removed = self.client.put(f"{URL}{v2['id']}/", {**header, 'lines': [
            {'id': v2['lines'][1]['id'], 'quantity': '1.00'}]}, format='json')
        self.assertEqual(removed.status_code, 409)
        saved = self.client.put(f"{URL}{v2['id']}/", {**header, 'lines': [
            *keep, {'id': v2['lines'][1]['id'], 'quantity': '1.00', 'unit_price': '150.00'},
            {'service_id': str(self.a.pk), 'quantity': '1'}]}, format='json')
        self.assertEqual(saved.status_code, 200, saved.content)
        lines = saved.json()['lines']
        self.assertEqual([(l['line_kind'], l['decision']) for l in lines],
                         [('carried', 'accepted'), ('replacement', 'pending'), ('additional', 'pending')])
        self.assertEqual(lines[0]['id'], v2['lines'][0]['id'])  # AC-12: ids estables al guardar
        self.assertEqual(ProformaLineDecisionModel.objects.filter(kind='carried').count(), 1)
        self.client.post(f"{URL}{v2['id']}/present/")
        old = self.get(p)
        self.assertEqual((old['status'], old['totals']['accepted'], old['decision_actions']), ('superseded', '100.00', []))
        self.assertEqual(self.get(v2)['totals']['accepted'], '100.00')
        self.assertEqual(ProformaLineDecisionModel.objects.filter(kind='decision').count(), 2)

    # AC-10
    def test_printable_exposes_only_commercial_data(self):
        p = self.presented()
        self.decide(p, [0], reference='SECRETO-REF')
        self.decide(p, [1], 'rejected', reason='SECRETO-MOTIVO')
        response = self.client.get(f"{URL}{p['id']}/printable/")
        self.assertEqual(response.status_code, 200)
        text = response.content.decode()
        for forbidden in ('SECRETO-REF', 'SECRETO-MOTIVO', 'dec-admin', 'recorded_by', 'decision_history',
                          'origin_line_id', p['lines'][0]['id'], 'reference'):
            self.assertNotIn(forbidden, text)
        body = response.json()
        self.assertEqual(body['totals'], {'proposed': '300.00', 'accepted': '100.00', 'pending': '0.00'})
        self.assertEqual(body['lines'][0]['decision'], 'accepted')
        draft = self.client.post(URL, {'customer_id': str(self.customer.pk), 'date': '2026-11-03', 'lines': []},
                                 format='json').json()
        self.assertEqual(self.client.get(f"{URL}{draft['id']}/printable/").status_code, 409)

    # AC-11
    def test_company_isolation_and_module_gate(self):
        p = self.presented()
        stranger = APIClient()
        stranger.force_authenticate(self.other)
        modules = DjangoCompanyModuleRepository(self.other.company_id)
        modules.enabled_keys()
        for key in ('catalog', 'services', 'quotations'):
            modules.enable(key)
        body = {'idempotency_key': str(uuid4()), 'decision': 'rejected', 'line_ids': [p['lines'][0]['id']]}
        self.assertEqual(stranger.post(f"{URL}{p['id']}/decisions/", body, format='json').status_code, 404)
        self.assertEqual(stranger.get(f"{URL}{p['id']}/printable/").status_code, 404)
        self.assertEqual(ProformaLineDecisionModel.objects.count(), 0)
        DjangoCompanyModuleRepository(self.admin.company_id).disable('quotations')
        response = self.client.post(f"{URL}{p['id']}/decisions/", body, format='json')
        self.assertEqual((response.status_code, response.json()['code']), (403, 'module_disabled'))

    # AC-12
    def test_saving_a_draft_keeps_line_ids(self):
        body = self.client.post(URL, {'customer_id': str(self.customer.pk), 'date': '2026-11-03', 'lines': [
            {'service_id': str(self.a.pk), 'quantity': '1'}]}, format='json').json()
        before = body['lines'][0]['id']
        self.client.put(f"{URL}{body['id']}/", {'customer_id': str(self.customer.pk), 'date': '2026-11-03',
                                                'lines': body['lines']}, format='json')
        self.assertEqual(list(ProformaLineModel.objects.values_list('id', flat=True)), [UUID(before)])

    # AC-13
    def test_deciding_creates_no_sale_collection_or_stock(self):
        before = {model: model.objects.count() for app in ('sales', 'inventory', 'purchases', 'expenses')
                  for model in apps.get_app_config(app).get_models()}
        p = self.presented()
        self.decide(p, [0])
        self.decide(p, [1], 'rejected')
        for model, count in before.items():
            self.assertEqual(model.objects.count(), count, model.__name__)
        self.assertEqual(ProformaModel.objects.count(), 1)
