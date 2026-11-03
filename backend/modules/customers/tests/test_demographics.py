from datetime import date
from unittest.mock import patch
from uuid import uuid4
from django.test import SimpleTestCase
from rest_framework.test import APITestCase
from modules.accounts.testing import make_admin, make_company, authenticate
from modules.customers.domain.demographics import Demographics, DemographicsInvalid
from modules.customers.infrastructure.django.models import CustomerModel
from modules.customers.infrastructure.django.demographics import CustomerDemographicsModel, CustomerDemographicsHistoryModel


class DemographicsTests(SimpleTestCase):
    today = date(2026, 11, 2)

    def test_missing_birth_does_not_presume_age(self):
        self.assertEqual(Demographics.validated(None, '', '', self.today).snapshot()['birth_date'], None)

    def test_under_18_requires_both_responsible_fields(self):
        for name, phone in (('', ''), ('Mamá', ''), ('', '76543210')):
            with self.subTest(name=name, phone=phone), self.assertRaises(DemographicsInvalid):
                Demographics.validated(date(2008, 11, 3), name, phone, self.today)
        value = Demographics.validated(date(2008, 11, 3), ' Mamá ', ' 76543210 ', self.today)
        self.assertEqual((value.responsible_name, value.responsible_phone), ('Mamá', '76543210'))

    def test_18th_birthday_is_adult(self):
        Demographics.validated(date(2008, 11, 2), '', '', self.today)

    def test_future_and_partial_contact_are_invalid(self):
        for birth, name, phone in ((date(2026, 11, 3), '', ''), (None, 'Tutor', ''), (None, '', '123')):
            with self.assertRaises(DemographicsInvalid):
                Demographics.validated(birth, name, phone, self.today)

    def test_february_29_reaches_age_on_march_1(self):
        with self.assertRaises(DemographicsInvalid):
            Demographics.validated(date(2008, 2, 29), '', '', date(2026, 2, 28))
        Demographics.validated(date(2008, 2, 29), '', '', date(2026, 3, 1))


class DemographicsApiTests(APITestCase):
    def setUp(self):
        self.company = make_company()
        self.user = make_admin(self.company)
        authenticate(self.client, self.user)
        self.customer = CustomerModel.objects.create(company_id=self.company.id, name='Paciente')
        self.url = f'/api/customers/{self.customer.id}/demographics/'

    def test_optional_default_and_audited_edit_without_changing_customer_contract(self):
        self.assertEqual(self.client.get(self.url).json(), Demographics().snapshot())
        response = self.client.patch(self.url, {'birth_date': '2000-01-01'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['birth_date'], '2000-01-01')
        history = self.client.get(self.url + 'history/').json()['results']
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['author_id'], self.user.id)
        self.assertIsNone(history[0]['before']['birth_date'])
        self.assertEqual(history[0]['after']['birth_date'], '2000-01-01')
        self.client.patch(self.url, {'birth_date': '2000-01-01'}, format='json')
        self.assertEqual(CustomerDemographicsHistoryModel.objects.count(), 1)
        body = self.client.get(f'/api/customers/{self.customer.id}/').json()
        self.assertNotIn('birth_date', body)
        self.assertNotIn('medical_history', body)

    @patch('modules.customers.api.demographics.timezone.localdate', return_value=date(2026, 11, 2))
    def test_minors_validation_rolls_back_and_partial_patch_revalidates(self, _today):
        invalid = self.client.patch(self.url, {'birth_date': '2010-01-01'}, format='json')
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('responsible_name', invalid.json())
        self.assertEqual(CustomerDemographicsHistoryModel.objects.count(), 0)
        valid = self.client.patch(self.url, {'birth_date': '2010-01-01', 'responsible_name': 'Madre',
                                             'responsible_phone': '76543210'}, format='json')
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(self.client.patch(self.url, {'responsible_phone': ''}, format='json').status_code, 400)
        self.assertEqual(CustomerDemographicsModel.objects.get().responsible_phone, '76543210')

    def test_foreign_customer_and_history_not_found(self):
        foreign = CustomerModel.objects.create(company_id=uuid4(), name='Ajeno')
        for suffix in ('', 'history/'):
            self.assertEqual(self.client.get(f'/api/customers/{foreign.id}/demographics/{suffix}').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/customers/{foreign.id}/demographics/', {}, format='json').status_code, 404)

    def test_audit_failure_rolls_back_data(self):
        with patch.object(CustomerDemographicsHistoryModel.objects, 'create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.patch(self.url, {'birth_date': '2000-01-01'}, format='json')
        self.assertFalse(CustomerDemographicsModel.objects.exists())

    def test_no_writable_history_route(self):
        self.assertEqual(self.client.post(self.url + 'history/', {}, format='json').status_code, 405)
