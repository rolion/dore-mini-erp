from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.modularity.infrastructure.django.models import CompanyModuleModel

LIST_URL = '/api/modules/'


def action_url(key, action):
    return f'/api/modules/{key}/{action}/'


def enabled_keys(client):
    return {m['key'] for m in client.get(LIST_URL).json() if m['enabled']}


class ModulesApiTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))


class ListModulesTests(ModulesApiTestCase):
    def test_defaults_on_first_access(self):  # AC-08, AC-09
        body = self.client.get(LIST_URL).json()
        self.assertEqual([m['key'] for m in body], ['access', 'catalog', 'customers', 'sales', 'expenses',
                                                    'reporting', 'purchases', 'inventory'])
        self.assertEqual(enabled_keys(self.client),
                         {'access', 'catalog', 'customers', 'sales', 'expenses', 'reporting'})

    def test_module_shape_and_base_flags(self):  # AC-02
        by_key = {m['key']: m for m in self.client.get(LIST_URL).json()}
        self.assertTrue(by_key['catalog']['is_base'])
        self.assertTrue(by_key['catalog']['enabled'])
        inventory = by_key['inventory']
        self.assertEqual(set(inventory), {'key', 'name', 'description', 'is_base', 'enabled', 'requires',
                                          'optional', 'missing_requires'})
        self.assertEqual(inventory['requires'], [{'key': 'catalog', 'name': 'Catálogo', 'enabled': True}])
        self.assertEqual([o['key'] for o in inventory['optional']], ['sales', 'purchases'])

    def test_repeated_reads_do_not_duplicate_defaults(self):  # EDGE-03
        self.client.get(LIST_URL)
        self.client.get(LIST_URL)
        self.assertEqual(CompanyModuleModel.objects.filter(company_id=self.company.id).count(), 4)

    def test_requires_authentication_and_company(self):  # AC-06, EDGE-06
        self.client.credentials()
        self.assertIn(self.client.get(LIST_URL).status_code, (401, 403))
        no_company = make_admin(None, username='root')
        no_company.company = None
        no_company.save()
        authenticate(self.client, no_company)
        self.assertEqual(self.client.get(LIST_URL).status_code, 403)

    def test_inactive_company_is_rejected(self):  # EDGE-06
        self.company.is_active = False
        self.company.save()
        self.assertEqual(self.client.get(LIST_URL).status_code, 403)


class EnableDisableTests(ModulesApiTestCase):
    def test_enable_inventory_only_for_this_company(self):  # AC-01, AC-04
        response = self.client.post(action_url('inventory', 'enable'))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()['enabled'])
        self.assertIn('inventory', enabled_keys(self.client))
        other = make_company('Empresa B')
        authenticate(self.client, make_admin(other, username='beto'))
        self.assertNotIn('inventory', enabled_keys(self.client))

    def test_enable_with_missing_dependencies_returns_names(self):  # AC-03
        self.client.post(action_url('reporting', 'disable'))
        self.client.post(action_url('sales', 'disable'))
        self.client.post(action_url('expenses', 'disable'))
        response = self.client.post(action_url('purchases', 'enable'))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['missing'], ['Gastos'])
        self.assertIn('Gastos', response.json()['detail'])
        self.assertNotIn('purchases', enabled_keys(self.client))

    def test_enable_is_idempotent(self):  # EDGE-02
        self.assertEqual(self.client.post(action_url('sales', 'enable')).status_code, 200)
        self.assertEqual(CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='sales').count(), 1)

    def test_disable_removes_module(self):  # AC-05
        self.client.post(action_url('reporting', 'disable'))
        response = self.client.post(action_url('customers', 'disable'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['enabled'])
        self.assertNotIn('customers', enabled_keys(self.client))
        self.assertEqual(self.client.post(action_url('customers', 'disable')).status_code, 200)  # EDGE-02

    def test_disable_blocked_by_dependents(self):  # INV-03, AC-05
        response = self.client.post(action_url('sales', 'disable'))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['dependents'], ['Reportes'])
        self.assertIn('sales', enabled_keys(self.client))

    def test_base_module_cannot_be_disabled(self):  # AC-02
        response = self.client.post(action_url('catalog', 'disable'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('catalog', enabled_keys(self.client))

    def test_unknown_module_is_404(self):  # EDGE-01
        self.assertEqual(self.client.post(action_url('nope', 'enable')).status_code, 404)
        self.assertEqual(self.client.post(action_url('nope', 'disable')).status_code, 404)

    def test_company_is_never_taken_from_the_request(self):  # AC-01, AC-06
        other = make_company('Empresa B')
        self.client.post(action_url('inventory', 'enable'), {'company_id': str(other.id)}, format='json')
        self.assertFalse(CompanyModuleModel.objects.filter(company_id=other.id).exists())

    def test_migration_creates_tables_only(self):  # AC-09
        from pathlib import Path

        import modules.modularity.migrations as package
        source = (Path(package.__file__).parent / '0001_initial.py').read_text(encoding='utf-8')
        self.assertNotIn('RunPython', source)
