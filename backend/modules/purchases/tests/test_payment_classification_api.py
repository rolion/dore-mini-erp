"""CONT-03: clasificación de pagos a proveedores (BD real)."""
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.expenses.infrastructure.django.models import ExpenseModel
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled
from modules.purchases.infrastructure.django.models import PaymentModel
from modules.purchases.tests.test_payment_api import PaymentApiTestCase, purchase_url

SETTING = '/api/purchases/payment-classification/'
CLASSIFICATIONS = '/api/accounting/classifications/'


class PaymentClassificationTestCase(PaymentApiTestCase):
    def classification(self, name='Pago a proveedores', direction='EXPENSE', client=None):
        response = (client or self.client).post(CLASSIFICATIONS, {'name': name, 'direction': direction}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def configure(self, classification_id, expected=200):
        response = self.client.put(SETTING, {'classification_id': classification_id}, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()


class ConfigurationTests(PaymentClassificationTestCase):
    def test_configure_read_and_clear(self):  # AC-02
        self.assertIsNone(self.client.get(SETTING).json()['classification'])
        supplier = self.classification()
        self.assertEqual(self.configure(supplier['id'])['classification']['name'], 'Pago a proveedores')
        self.assertEqual(self.client.get(SETTING).json()['classification']['id'], supplier['id'])
        self.assertIsNone(self.configure(None)['classification'])

    def test_rejects_income_inactive_unknown_and_other_company(self):  # AC-02
        income = self.classification('Ventas', 'INCOME')
        inactive = self.classification('Vieja')
        self.client.post(f'{CLASSIFICATIONS}{inactive["id"]}/deactivate/')
        other = APIClient()
        authenticate(other, make_admin(make_company('Empresa B'), username='beto'))
        foreign = self.classification('Ajena', client=other)
        for bad in (income['id'], inactive['id'], foreign['id'], '3f2c1b7e-0000-4000-8000-000000000000'):
            self.assertIn('classification_id', self.configure(bad, expected=400))
        self.assertIsNone(self.client.get(SETTING).json()['classification'])

    def test_requires_an_admin_with_a_company(self):  # AC-05
        loose = APIClient()
        authenticate(loose, get_user_model().objects.create_user(username='sin-empresa', password='x'))
        body = {'classification_id': None}
        self.assertEqual(loose.put(SETTING, body, format='json').status_code, 403)
        self.assertEqual(APIClient().put(SETTING, body, format='json').status_code, 401)


class PaymentSnapshotTests(PaymentClassificationTestCase):
    def test_payment_uses_the_configured_classification_and_creates_no_expense(self):  # AC-04
        supplier = self.classification()
        self.configure(supplier['id'])
        paid = self.pay(self.confirmed_purchase())
        self.assertEqual(paid['classification']['id'], supplier['id'])
        self.assertEqual(ExpenseModel.objects.count(), 0)

    def test_changing_the_setting_keeps_recorded_payments(self):  # AC-03
        first, second = self.classification('Proveedores'), self.classification('Otros')
        self.configure(first['id'])
        paid = self.pay(self.confirmed_purchase())
        self.configure(second['id'])
        self.configure(None)
        self.assertEqual(str(PaymentModel.objects.get(pk=paid['id']).classification_id), first['id'])

    def test_payment_without_configuration_is_saved_when_accounting_is_off(self):  # AC-07
        self.assertIsNone(self.pay(self.confirmed_purchase())['classification'])


class CoverageTests(PaymentClassificationTestCase):
    def setUp(self):
        super().setUp()
        set_enabled(self.company, (*DEFAULT_ENABLED_KEYS, 'purchases', 'accounting'))

    def test_covered_payment_without_configuration_is_rejected(self):  # AC-07
        purchase = self.confirmed_purchase()
        body = self.pay(purchase, expected=400)
        self.assertEqual(body['code'], 'classification_not_configured')
        self.assertEqual(PaymentModel.objects.count(), 0)

    def test_covered_payment_with_inactive_classification_is_rejected(self):  # AC-07
        supplier = self.classification()
        self.configure(supplier['id'])
        self.client.post(f'{CLASSIFICATIONS}{supplier["id"]}/deactivate/')
        self.assertEqual(self.pay(self.confirmed_purchase(), expected=400)['code'], 'classification_invalid')

    def test_covered_payment_with_configuration_is_saved(self):  # AC-04, AC-07
        supplier = self.classification()
        self.configure(supplier['id'])
        purchase = self.confirmed_purchase()
        first = self.pay(purchase, '20.00')
        second = self.pay(purchase, '30.00')
        self.assertEqual({first['classification']['id'], second['classification']['id']}, {supplier['id']})
        self.assertEqual(self.client.get(purchase_url(purchase['id'], 'payments/')).json()['results'][0]
                         ['classification']['name'], 'Pago a proveedores')
