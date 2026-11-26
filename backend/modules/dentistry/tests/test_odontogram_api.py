from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.customers.infrastructure.django.models import CustomerModel
from modules.dentistry.infrastructure.evaluation_models import EvaluationModel
from modules.dentistry.infrastructure.proforma_models import DentalProformaLineModel, DentalProformaModel
from modules.personnel.infrastructure.django.models import ProfessionalModel

ROOT = '/api/dentistry/'
PATIENTS = ROOT + 'patients/'


def enable(client):
    response = client.post('/api/modules/dentistry/enable/', {}, format='json')
    assert response.status_code == 200, response.content


class EvaluationApiTests(APITestCase):
    def setUp(self):
        self.company = make_company()
        self.user = make_admin(self.company)
        authenticate(self.client, self.user)
        enable(self.client)
        self.customer = CustomerModel.objects.create(company_id=self.company.id, name='Ana', phone='+59176543210')
        self.client.post(PATIENTS, {'customer_id': str(self.customer.id)}, format='json')
        self.list_url = f'{PATIENTS}{self.customer.id}/evaluations/'
        self.today = timezone.localdate()

    def body(self, **extra):
        data = {'dentition': 'mixed', 'clinical_date': self.today.isoformat(),
                'findings': [{'piece': 54, 'condition': 'caries', 'surfaces': ['O']},
                             {'piece': 16, 'condition': 'filling', 'surfaces': ['O', 'M']}],
                'general_findings': []}
        data.update(extra)
        return data

    def create(self, **extra):
        return self.client.post(self.list_url, self.body(**extra), format='json')

    def confirmed(self, **extra):
        draft = self.create(**extra).json()
        response = self.client.post(f'{ROOT}evaluations/{draft["id"]}/confirm/')
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_catalog(self):  # API-01
        data = self.client.get(ROOT + 'odontogram/catalog/').json()
        self.assertTrue(data['pending_clinical_validation'])
        self.assertEqual([c['code'] for c in data['conditions']][:2], ['healthy', 'caries'])
        self.assertEqual(len(data['teeth']['permanent']), 32)

    def test_mixed_dentition_records_temporary_and_permanent(self):  # AC-01, AC-07
        response = self.create()
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual((data['status'], data['sequence']), ('draft', 1))
        self.assertEqual({f['piece'] for f in data['findings']}, {54, 16})
        self.assertEqual(data['author']['id'], self.user.id)
        self.assertEqual(data['allowed_actions'], ['edit', 'confirm', 'discard'])
        self.assertEqual(self.client.get(f'{ROOT}evaluations/{data["id"]}/').json()['findings'], data['findings'])

    def test_initial_version_is_kept_after_another_evaluation(self):  # AC-02
        first = self.confirmed()
        second = self.confirmed(findings=[{'piece': 11, 'condition': 'healthy'}], dentition='permanent')
        listing = self.client.get(self.list_url).json()
        self.assertEqual([row['sequence'] for row in listing['results']], [2, 1])
        old = self.client.get(f'{ROOT}evaluations/{first["id"]}/').json()
        self.assertEqual({f['piece'] for f in old['findings']}, {54, 16})
        self.assertEqual(second['sequence'], 2)
        self.assertEqual(old['status'], 'confirmed')
        self.assertEqual(old['allowed_actions'], ['amend'])

    def test_invalid_piece_and_surface_are_rejected(self):  # AC-03, AC-04
        for findings in ([{'piece': 19, 'condition': 'healthy'}],
                         [{'piece': 54, 'condition': 'healthy'}],
                         [{'piece': 11, 'condition': 'caries', 'surfaces': ['O']}],
                         [{'piece': 36, 'condition': 'caries', 'surfaces': ['P']}]):
            response = self.create(dentition='permanent', findings=findings)
            self.assertEqual(response.status_code, 400, findings)
            self.assertIn('findings', response.json())
        self.assertEqual(EvaluationModel.objects.count(), 0)

    def test_catalog_rules_over_api(self):  # AC-10
        for findings in ([{'piece': 16, 'condition': 'other'}],
                         [{'piece': 16, 'condition': 'healthy'}, {'piece': 16, 'condition': 'crown'}],
                         [{'piece': 16, 'condition': 'caries', 'surfaces': ['O']},
                          {'piece': 16, 'condition': 'filling', 'surfaces': ['O']}]):
            self.assertEqual(self.create(findings=findings).status_code, 400)
        self.assertEqual(self.create(clinical_date=(self.today + timedelta(days=1)).isoformat()).status_code, 400)

    def test_draft_can_be_edited_and_discarded_but_not_confirmed_one(self):  # AC-05
        draft = self.create().json()
        url = f'{ROOT}evaluations/{draft["id"]}/'
        edited = self.client.put(url, self.body(findings=[{'piece': 55, 'condition': 'healthy'}]), format='json')
        self.assertEqual(edited.status_code, 200, edited.content)
        self.assertEqual([f['piece'] for f in edited.json()['findings']], [55])
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(EvaluationModel.objects.count(), 0)
        confirmed = self.confirmed()
        url = f'{ROOT}evaluations/{confirmed["id"]}/'
        before = self.client.get(url).json()
        self.assertEqual(self.client.put(url, self.body(findings=[{'piece': 55, 'condition': 'healthy'}]),
                                         format='json').status_code, 409)
        self.assertEqual(self.client.delete(url).status_code, 409)
        self.assertEqual(self.client.post(url + 'confirm/').status_code, 409)
        self.assertEqual(self.client.get(url).json(), before)

    def test_confirm_requires_a_finding(self):
        empty = self.create(findings=[]).json()
        self.assertEqual(self.client.post(f'{ROOT}evaluations/{empty["id"]}/confirm/').status_code, 400)

    def test_second_draft_is_conflict(self):
        self.create()
        self.assertEqual(self.create().status_code, 409)

    def test_amendment_links_previous_and_keeps_it(self):  # AC-06
        original = self.confirmed()
        url = f'{ROOT}evaluations/{original["id"]}/amend/'
        self.assertEqual(self.client.post(url, {'reason': '  '}, format='json').status_code, 400)
        response = self.client.post(url, {'reason': 'Superficie equivocada'}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        amendment = response.json()
        self.assertEqual((amendment['status'], amendment['amends_id'], amendment['amends_sequence']),
                         ('draft', original['id'], 1))
        self.assertEqual(amendment['amendment_reason'], 'Superficie equivocada')
        self.assertEqual(self.client.post(url, {'reason': 'otra'}, format='json').status_code, 409)  # ya hay borrador
        self.client.put(f'{ROOT}evaluations/{amendment["id"]}/',
                        self.body(findings=[{'piece': 16, 'condition': 'filling', 'surfaces': ['O']}]), format='json')
        self.client.post(f'{ROOT}evaluations/{amendment["id"]}/confirm/')
        old = self.client.get(f'{ROOT}evaluations/{original["id"]}/').json()
        self.assertEqual((old['replaced_by_id'], old['replaced_by_sequence']), (amendment['id'], 2))
        self.assertEqual(len(old['findings']), 2)
        self.assertEqual(old['allowed_actions'], [])
        self.assertEqual(self.client.post(url, {'reason': 'otra'}, format='json').status_code, 409)

    def test_general_findings_are_kept_apart(self):  # AC-08
        data = self.create(findings=[], general_findings=[{'diagnosis': 'Bruxismo', 'notes': 'Nocturno'}]).json()
        self.assertEqual(data['findings'], [])
        self.assertEqual(data['general_findings'][0]['diagnosis'], 'Bruxismo')
        self.assertEqual(self.client.post(f'{ROOT}evaluations/{data["id"]}/confirm/').status_code, 200)

    def test_professional_must_belong_to_company(self):
        mine = ProfessionalModel.objects.create(company_id=self.company.id, name='Dra. Paz', created_by=1, updated_by=1)
        other = ProfessionalModel.objects.create(company_id=uuid4(), name='Ajeno', created_by=1, updated_by=1)
        self.assertEqual(self.create(professional_id=str(other.id)).status_code, 400)
        data = self.create(professional_id=str(mine.id)).json()
        self.assertEqual(data['professional'], {'id': str(mine.id), 'name': 'Dra. Paz'})

    def test_author_cannot_be_spoofed(self):
        data = self.create(created_by=999, author={'id': 999}).json()
        self.assertEqual(data['author']['id'], self.user.id)

    def test_company_isolation(self):  # AC-09
        draft = self.create().json()
        other_company = make_company('Otra')
        other_user = make_admin(other_company, username='bea')
        other = APIClient()
        authenticate(other, other_user)
        enable(other)
        self.assertEqual(other.get(f'{ROOT}evaluations/{draft["id"]}/').status_code, 404)
        self.assertEqual(other.put(f'{ROOT}evaluations/{draft["id"]}/', self.body(), format='json').status_code, 404)
        self.assertEqual(other.post(f'{ROOT}evaluations/{draft["id"]}/confirm/').status_code, 404)
        self.assertEqual(other.get(self.list_url).status_code, 404)

    def test_permissions_and_module_gate(self):  # AC-09
        draft = self.create().json()
        urls = (self.list_url, f'{ROOT}evaluations/{draft["id"]}/', ROOT + 'odontogram/catalog/')
        with patch('config.permissions.has_clinical_access', return_value=False):
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(self.list_url, self.body(), format='json').status_code, 403)
        self.user.role = 'reception'
        self.user.save()
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.user.role = 'admin'
        self.user.save()
        self.client.post('/api/modules/dentistry/disable/')
        for url in urls:
            response = self.client.get(url)
            self.assertEqual((response.status_code, response.json()['code']), (403, 'module_disabled'))
        self.client.credentials()
        self.assertIn(self.client.get(self.list_url).status_code, (401, 403))

    def test_archived_patient_is_read_only(self):  # INV-12
        confirmed = self.confirmed()
        draft = self.client.post(f'{ROOT}evaluations/{confirmed["id"]}/amend/', {'reason': 'x'}, format='json').json()
        self.client.post(f'{PATIENTS}{self.customer.id}/archive/')
        self.assertEqual(self.create().status_code, 409)
        self.assertEqual(self.client.put(f'{ROOT}evaluations/{draft["id"]}/', self.body(), format='json').status_code,
                         409)
        self.assertEqual(self.client.post(f'{ROOT}evaluations/{draft["id"]}/confirm/').status_code, 409)
        self.assertEqual(self.client.delete(f'{ROOT}evaluations/{draft["id"]}/').status_code, 409)
        self.assertEqual(self.client.get(self.list_url).status_code, 200)
        detail = self.client.get(f'{ROOT}evaluations/{confirmed["id"]}/').json()
        self.assertEqual(detail['allowed_actions'], [])

    def test_unknown_patient_is_404(self):
        self.assertEqual(self.client.get(f'{PATIENTS}{uuid4()}/evaluations/').status_code, 404)
        self.assertEqual(self.client.post(f'{PATIENTS}{uuid4()}/evaluations/', self.body(), format='json').status_code,
                         404)

    def test_does_not_touch_proformas(self):  # AC-13
        before = (DentalProformaModel.objects.count(), DentalProformaLineModel.objects.count())
        self.confirmed()
        self.assertEqual((DentalProformaModel.objects.count(), DentalProformaLineModel.objects.count()), before)
