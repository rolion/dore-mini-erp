"""CONT-03: asociación de clasificaciones de egreso a categorías de Gastos (BD real)."""
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.expenses.infrastructure.django.models import ExpenseModel
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled

CATEGORIES = '/api/expense-categories/'
EXPENSES = '/api/expenses/'
CLASSIFICATIONS = '/api/accounting/classifications/'


class ClassificationApiTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))

    def classification(self, name='Alquiler', direction='EXPENSE', client=None):
        response = (client or self.client).post(CLASSIFICATIONS, {'name': name, 'direction': direction}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def category(self, name='Alquiler'):
        response = self.client.post(CATEGORIES, {'name': name}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def associate(self, category, classification_id, expected=200):
        response = self.client.put(f'{CATEGORIES}{category["id"]}/classification/',
                                   {'classification_id': classification_id}, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def expense(self, category, expected=201, **extra):
        body = {'description': 'Mes', 'amount': '500.00', 'category_id': category['id'],
                'expense_date': timezone.localdate().isoformat(), **extra}
        response = self.client.post(EXPENSES, body, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()


class AssociationApiTests(ClassificationApiTestCase):
    def test_associates_and_applies_to_new_expense(self):  # AC-01
        rent, category = self.classification(), self.category()
        updated = self.associate(category, rent['id'])
        self.assertEqual(updated['classification']['id'], rent['id'])
        self.assertEqual(self.expense(category)['classification']['name'], 'Alquiler')
        self.assertEqual(self.client.get(CATEGORIES).json()['results'][0]['classification']['id'], rent['id'])

    def test_rejects_income_inactive_unknown_and_other_company(self):  # AC-02
        category = self.category()
        income = self.classification('Ventas', 'INCOME')
        inactive = self.classification('Vieja')
        self.client.post(f'{CLASSIFICATIONS}{inactive["id"]}/deactivate/')
        other_client = APIClient()
        authenticate(other_client, make_admin(make_company('Empresa B'), username='beto'))
        foreign = self.classification('Ajena', client=other_client)
        for bad in (income['id'], inactive['id'], foreign['id'], '3f2c1b7e-0000-4000-8000-000000000000'):
            body = self.associate(category, bad, expected=400)
            self.assertIn('classification_id', body)
        self.assertIsNone(self.client.get(f'{CATEGORIES}{category["id"]}/').json()['classification'])

    def test_changing_the_association_does_not_touch_recorded_expenses(self):  # AC-03
        first, second = self.classification('Alquiler'), self.classification('Local')
        category = self.category()
        self.associate(category, first['id'])
        recorded = self.expense(category)
        self.associate(category, second['id'])
        self.associate(category, None)
        stored = ExpenseModel.objects.get(pk=recorded['id'])
        self.assertEqual(str(stored.classification_id), first['id'])
        self.assertIsNone(self.expense(category)['classification'])

    def test_requires_an_admin_with_a_company(self):  # AC-05
        category = self.category()
        rent = self.classification()
        from django.contrib.auth import get_user_model
        loose = get_user_model().objects.create_user(username='sin-empresa', password='x')
        client = APIClient()
        authenticate(client, loose)
        url = f'{CATEGORIES}{category["id"]}/classification/'
        self.assertEqual(client.put(url, {'classification_id': rent['id']}, format='json').status_code, 403)
        self.assertEqual(APIClient().put(url, {'classification_id': rent['id']}, format='json').status_code, 401)

    def test_other_company_category_is_not_found(self):  # AC-02
        category = self.category()
        other_client = APIClient()
        authenticate(other_client, make_admin(make_company('Empresa B'), username='beto'))
        foreign = self.classification('Ajena', client=other_client)
        response = other_client.put(f'{CATEGORIES}{category["id"]}/classification/',
                                    {'classification_id': foreign['id']}, format='json')
        self.assertEqual(response.status_code, 404)


class SnapshotApiTests(ClassificationApiTestCase):
    def test_voided_expense_keeps_its_snapshot(self):  # INV-02
        rent, category = self.classification(), self.category()
        self.associate(category, rent['id'])
        recorded = self.expense(category)
        voided = self.client.post(f'{EXPENSES}{recorded["id"]}/void/').json()
        self.assertEqual(voided['classification']['id'], rent['id'])

    def test_editing_without_changing_category_keeps_the_snapshot(self):  # INV-02
        first, second = self.classification('Alquiler'), self.classification('Local')
        category = self.category()
        self.associate(category, first['id'])
        recorded = self.expense(category)
        self.associate(category, second['id'])
        edited = self.client.patch(f'{EXPENSES}{recorded["id"]}/', {'description': 'Otro'}, format='json').json()
        self.assertEqual(edited['classification']['id'], first['id'])

    def test_disabled_accounting_saves_without_configuration(self):  # AC-06
        category = self.category()
        self.assertIsNone(self.expense(category)['classification'])


class CoverageApiTests(ClassificationApiTestCase):
    def setUp(self):
        super().setUp()
        set_enabled(self.company, (*DEFAULT_ENABLED_KEYS, 'accounting'))

    def test_covered_expense_no_longer_requires_a_classification(self):  # GAS-01: lo exige la cuenta, no la clasificación
        category = self.category()
        body = self.expense(category, expected=400)
        self.assertEqual(body['code'], 'posting_configuration_missing')
        self.assertNotIn('classification', body['code'])
        self.assertEqual(ExpenseModel.objects.count(), 0)

    def test_expense_before_the_cutoff_is_saved_without_configuration(self):  # AC-06
        category = self.category()
        self.client.get('/api/accounting/settings/')  # completa el corte (hoy)
        saved = self.expense(category, expense_date='2020-01-01')
        self.assertIsNone(saved['classification'])
