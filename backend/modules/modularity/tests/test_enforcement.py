"""PB-MOD-002: la API de negocio rechaza los módulos deshabilitados de la empresa del usuario."""
from uuid import uuid4

from rest_framework.test import APIClient, APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.customers.infrastructure.django.models import CustomerModel
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.infrastructure.django.models import CompanyModuleModel, CompanySettingsModel

CUSTOMERS_OFF = 'El módulo Clientes no está habilitado.'
ID = uuid4()

# (módulo, método, ruta): cubre cada vista de negocio; el permiso se evalúa antes de resolver el recurso.
ROUTES = [
    ('customers', 'get', '/api/customers/'), ('customers', 'post', '/api/customers/'),
    ('customers', 'get', f'/api/customers/{ID}/'), ('customers', 'patch', f'/api/customers/{ID}/'),
    ('customers', 'post', f'/api/customers/{ID}/activate/'), ('customers', 'post', f'/api/customers/{ID}/deactivate/'),
    ('sales', 'get', '/api/orders/'), ('sales', 'post', '/api/orders/'),
    ('sales', 'get', f'/api/orders/{ID}/'), ('sales', 'patch', f'/api/orders/{ID}/'),
    ('sales', 'get', f'/api/orders/{ID}/items/'), ('sales', 'post', f'/api/orders/{ID}/items/'),
    ('sales', 'patch', f'/api/orders/{ID}/items/{ID}/'), ('sales', 'delete', f'/api/orders/{ID}/items/{ID}/'),
    ('sales', 'post', f'/api/orders/{ID}/discount/'), ('sales', 'post', f'/api/orders/{ID}/prepare/'),
    ('sales', 'post', f'/api/orders/{ID}/ready/'), ('sales', 'post', f'/api/orders/{ID}/deliver/'),
    ('sales', 'post', f'/api/orders/{ID}/cancel/'), ('sales', 'post', f'/api/orders/{ID}/payments/'),
    ('purchases', 'get', '/api/suppliers/'), ('purchases', 'post', '/api/suppliers/'),
    ('purchases', 'get', f'/api/suppliers/{ID}/'), ('purchases', 'patch', f'/api/suppliers/{ID}/'),
    ('purchases', 'post', f'/api/suppliers/{ID}/activate/'), ('purchases', 'post', f'/api/suppliers/{ID}/deactivate/'),
    ('purchases', 'get', '/api/purchases/'), ('purchases', 'post', '/api/purchases/'),
    ('purchases', 'get', f'/api/purchases/{ID}/'), ('purchases', 'patch', f'/api/purchases/{ID}/'),
    ('purchases', 'post', f'/api/purchases/{ID}/confirm/'), ('purchases', 'post', f'/api/purchases/{ID}/cancel/'),
    ('expenses', 'get', '/api/expenses/'), ('expenses', 'post', '/api/expenses/'),
    ('expenses', 'get', f'/api/expenses/{ID}/'), ('expenses', 'patch', f'/api/expenses/{ID}/'),
    ('expenses', 'post', f'/api/expenses/{ID}/void/'),
    ('expenses', 'get', '/api/expense-categories/'), ('expenses', 'post', '/api/expense-categories/'),
    ('expenses', 'get', f'/api/expense-categories/{ID}/'), ('expenses', 'patch', f'/api/expense-categories/{ID}/'),
    ('expenses', 'post', f'/api/expense-categories/{ID}/activate/'),
    ('expenses', 'post', f'/api/expense-categories/{ID}/deactivate/'),
    ('inventory', 'get', '/api/units/'), ('inventory', 'post', '/api/units/'),
    ('inventory', 'get', f'/api/units/{ID}/'), ('inventory', 'patch', f'/api/units/{ID}/'),
    ('inventory', 'post', f'/api/units/{ID}/activate/'), ('inventory', 'post', f'/api/units/{ID}/deactivate/'),
    ('inventory', 'get', '/api/warehouses/'), ('inventory', 'post', '/api/warehouses/'),
    ('inventory', 'get', f'/api/warehouses/{ID}/'), ('inventory', 'patch', f'/api/warehouses/{ID}/'),
    ('inventory', 'post', f'/api/warehouses/{ID}/activate/'), ('inventory', 'post', f'/api/warehouses/{ID}/deactivate/'),
    ('inventory', 'post', f'/api/warehouses/{ID}/make-default/'),
    ('reporting', 'get', '/api/reports/dashboard/'), ('reporting', 'get', '/api/reports/sales/'),
    ('reporting', 'get', '/api/reports/expenses/'), ('reporting', 'get', '/api/reports/sales-by-channel/'),
    ('reporting', 'get', '/api/reports/top-products/'), ('reporting', 'get', '/api/reports/top-customers/'),
    ('reporting', 'get', '/api/reports/pending/'),
]


def set_enabled(company, keys):
    """Fija directamente los módulos no base habilitados de la empresa (inicializada)."""
    CompanySettingsModel.objects.get_or_create(company_id=company.id)
    CompanyModuleModel.objects.filter(company_id=company.id).delete()
    CompanyModuleModel.objects.bulk_create([CompanyModuleModel(company_id=company.id, module_key=k) for k in keys])


class EnforcementTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)

    def assert_disabled(self, response, module):
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(response.json(), {'detail': 'Módulo no habilitado', 'code': 'module_disabled', 'module': module})


class DisabledModuleTests(EnforcementTestCase):
    def test_every_route_of_a_disabled_module_is_rejected(self):  # AC-01
        for module in ('customers', 'sales', 'expenses', 'reporting', 'purchases'):
            set_enabled(self.company, [k for k in DEFAULT_ENABLED_KEYS if k != module])
            for _, method, path in (r for r in ROUTES if r[0] == module):
                with self.subTest(f'{method.upper()} {path}'):
                    self.assert_disabled(getattr(self.client, method)(path, {}, format='json'), module)

    def test_top_customers_needs_customers_too(self):  # AC-08, EDGE-02
        set_enabled(self.company, [k for k in DEFAULT_ENABLED_KEYS if k != 'customers'])
        self.assert_disabled(self.client.get('/api/reports/top-customers/'), 'customers')
        self.assertEqual(self.client.get('/api/reports/sales/').status_code, 200)

    def test_rejected_request_does_not_touch_data(self):  # AC-01
        set_enabled(self.company, [k for k in DEFAULT_ENABLED_KEYS if k != 'customers'])
        self.assert_disabled(self.client.post('/api/customers/', {'name': 'Ana'}, format='json'), 'customers')
        self.assertEqual(CustomerModel.objects.count(), 0)

    def test_base_catalog_module_is_always_allowed(self):  # AC-06, INV-03
        set_enabled(self.company, [])
        self.assertEqual(self.client.get('/api/products/').status_code, 200)

    def test_enabled_modules_keep_working(self):  # AC-02
        for path in ('/api/customers/', '/api/orders/', '/api/expenses/', '/api/expense-categories/',
                     '/api/reports/dashboard/', '/api/reports/top-customers/', '/api/products/'):
            with self.subTest(path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_modules_endpoints_are_not_gated_by_a_module(self):  # AC-06
        set_enabled(self.company, [])
        self.assertEqual(self.client.get('/api/modules/').status_code, 200)

    def test_first_request_of_an_uninitialized_company_uses_defaults(self):  # EDGE-01
        company = make_company('Empresa nueva')
        client = APIClient()
        authenticate(client, make_admin(company, username='nueva'))
        self.assertEqual(client.get('/api/customers/').status_code, 200)
        stored = CompanyModuleModel.objects.filter(company_id=company.id).values_list('module_key', flat=True)
        self.assertEqual(sorted(stored), sorted(DEFAULT_ENABLED_KEYS))


class CompanyIsolationTests(EnforcementTestCase):
    def test_another_company_configuration_does_not_apply(self):  # AC-03
        other = make_company('Empresa B')
        other_client = APIClient()
        authenticate(other_client, make_admin(other, username='beto'))
        set_enabled(other, [])
        self.assertEqual(self.client.get('/api/customers/').status_code, 200)
        self.assert_disabled(other_client.get('/api/customers/'), 'customers')

    def test_company_sent_by_the_client_is_ignored(self):  # AC-03, INV-01
        other = make_company('Empresa B')
        set_enabled(other, [])
        response = self.client.get(f'/api/customers/?company_id={other.id}', HTTP_X_COMPANY_ID=str(other.id))
        self.assertEqual(response.status_code, 200)
        set_enabled(self.company, [])
        self.assert_disabled(self.client.get(f'/api/customers/?company_id={other.id}'), 'customers')

    def test_authentication_and_company_are_checked_before_the_module(self):  # AC-05
        set_enabled(self.company, [])
        self.client.credentials()
        response = self.client.get('/api/customers/')
        self.assertIn(response.status_code, (401, 403))
        self.assertNotIn('code', response.json())
        orphan = make_admin(None, username='huerfano')
        orphan.company = None
        orphan.save()
        authenticate(self.client, orphan)
        response = self.client.get('/api/customers/')
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('code', response.json())


class PermissionOrderTests(EnforcementTestCase):
    """AC-05: autenticación, empresa activa y rol se evalúan antes que el módulo; también en OPTIONS y HEAD."""

    def test_missing_token_is_401_without_module_code(self):
        set_enabled(self.company, [])
        self.client.credentials()
        response = self.client.get('/api/customers/')
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('code', response.json())

    def test_inactive_company_is_rejected_before_the_module(self):
        set_enabled(self.company, [])
        self.company.is_active = False
        self.company.save()
        response = self.client.get('/api/customers/')
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('code', response.json())

    def test_head_and_options_are_also_gated(self):
        set_enabled(self.company, [k for k in DEFAULT_ENABLED_KEYS if k != 'customers'])
        for method in ('head', 'options'):
            with self.subTest(method):
                self.assertEqual(getattr(self.client, method)('/api/customers/').status_code, 403)


class ConfigurationChangeTests(EnforcementTestCase):
    def test_toggling_a_module_takes_effect_on_the_next_request(self):  # AC-04
        self.assertEqual(self.client.get('/api/customers/').status_code, 200)
        self.assertEqual(self.client.post('/api/modules/customers/disable/').status_code, 200)
        self.assert_disabled(self.client.get('/api/customers/'), 'customers')
        self.assertEqual(self.client.post('/api/modules/customers/enable/').status_code, 200)
        self.assertEqual(self.client.get('/api/customers/').status_code, 200)

    def test_data_is_preserved_while_disabled(self):  # AC-11
        self.client.post('/api/customers/', {'name': 'Ana'}, format='json')
        self.client.post('/api/modules/customers/disable/')
        self.client.post('/api/modules/customers/enable/')
        names = [c['name'] for c in self.client.get('/api/customers/').json()['results']]
        self.assertEqual(names, ['Ana'])


class CustomersOptionalIntegrationTests(EnforcementTestCase):
    def setUp(self):
        super().setUp()
        self.customer = CustomerModel.objects.create(company_id=self.company.id, name='Ana')
        payload = {'sales_channel': 'STORE', 'customer_id': str(self.customer.id)}
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        self.order_id = response.json()['id']
        set_enabled(self.company, [k for k in DEFAULT_ENABLED_KEYS if k != 'customers'])

    def test_sales_keeps_working_without_customers(self):  # AC-07
        response = self.client.post('/api/orders/', {'sales_channel': 'STORE'}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()['customer'])
        self.assertEqual(self.client.get('/api/orders/').status_code, 200)

    def test_assigning_a_customer_is_rejected(self):  # AC-07
        payload = {'sales_channel': 'STORE', 'customer_id': str(self.customer.id)}
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'customer_id': [CUSTOMERS_OFF]})
        response = self.client.patch(f'/api/orders/{self.order_id}/', {'customer_id': str(uuid4())}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'customer_id': [CUSTOMERS_OFF]})

    def test_editing_other_fields_keeps_the_stored_customer(self):  # AC-11
        response = self.client.patch(f'/api/orders/{self.order_id}/', {'notes': 'Sin picante'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.client.post('/api/modules/customers/enable/')
        self.assertEqual(self.client.get(f'/api/orders/{self.order_id}/').json()['customer']['name'], 'Ana')

    def test_filtering_by_customer_is_rejected(self):  # AC-07
        response = self.client.get(f'/api/orders/?customer_id={self.customer.id}')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'customer_id': [CUSTOMERS_OFF]})

    def test_existing_orders_show_no_customer_until_it_is_enabled_again(self):  # AC-07, AC-11
        self.assertIsNone(self.client.get(f'/api/orders/{self.order_id}/').json()['customer'])
        self.assertIsNone(self.client.get('/api/orders/').json()['results'][0]['customer'])
        self.client.post('/api/modules/customers/enable/')
        self.assertEqual(self.client.get(f'/api/orders/{self.order_id}/').json()['customer']['name'], 'Ana')

    def test_reports_other_than_top_customers_work(self):  # AC-08
        for path in ('/api/reports/dashboard/', '/api/reports/sales/', '/api/reports/pending/'):
            with self.subTest(path):
                self.assertEqual(self.client.get(path).status_code, 200)
