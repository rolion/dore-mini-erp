"""PB-MOD-005: Producción y Costeo, capacidades, bloqueos y fecha de adopción (API)."""
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from shared import module_extensions
from shared.module_extensions import Blocker

LIST_URL = '/api/modules/'


def action_url(key, action):
    return f'/api/modules/{key}/{action}/'


class ProductionAndCostingTests(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))
        module_extensions.reset()
        self.addCleanup(module_extensions.reset)

    def enabled(self):
        return {m['key'] for m in self.client.get(LIST_URL).json() if m['enabled']}

    def module(self, key):
        return next(m for m in self.client.get(LIST_URL).json() if m['key'] == key)

    def enable_production(self):
        self.assertEqual(self.client.post(action_url('inventory', 'enable')).status_code, 200)
        response = self.client.post(action_url('production', 'enable'))
        self.assertEqual(response.status_code, 200, response.content)

    def test_library_defaults_keep_production_and_costing_off(self):  # AC-01
        self.assertFalse({'production', 'costing'} & self.enabled())

    def test_production_needs_inventory_and_not_purchases(self):  # AC-01, AC-02
        response = self.client.post(action_url('production', 'enable'))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['missing'], ['Inventario'])
        self.enable_production()
        self.assertNotIn('purchases', self.enabled())
        self.assertNotIn('costing', self.enabled())

    def test_costing_needs_production(self):  # AC-02
        response = self.client.post(action_url('costing', 'enable'))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['missing'], ['Producción'])

    def test_costing_blocked_without_valuation(self):  # AC-02, AC-03
        self.enable_production()
        response = self.client.post(action_url('costing', 'enable'))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['missing_capabilities'], ['Valoración de Inventario'])
        self.assertNotIn('costing', self.enabled())
        costing = self.module('costing')
        self.assertEqual(costing['capabilities'], [{'key': 'inventory.valuation',
                                                    'label': 'Valoración de Inventario', 'available': False}])
        self.assertIsNone(costing['adopted_at'])

    def test_costing_enables_with_valuation_and_fixes_adoption_date(self):  # AC-05
        self.enable_production()
        calls = []
        module_extensions.register_capability('inventory.valuation', lambda company_id: company_id == self.company.id)
        module_extensions.register_enable_hook('costing', lambda company_id, at: calls.append((company_id, at)))
        response = self.client.post(action_url('costing', 'enable'))
        self.assertEqual(response.status_code, 200, response.content)
        adopted = response.json()['adopted_at']
        self.assertIsNotNone(adopted)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], self.company.id)
        self.assertEqual(self.module('costing')['adopted_at'], adopted)
        self.client.post(action_url('costing', 'enable'))
        self.assertEqual(len(calls), 1)

    def test_capability_is_per_company(self):  # EDGE-03
        module_extensions.register_capability('inventory.valuation', lambda company_id: company_id == self.company.id)
        authenticate(self.client, make_admin(make_company('Empresa B'), username='beto'))
        self.assertFalse(self.module('costing')['capabilities'][0]['available'])

    def test_failed_adoption_hook_leaves_costing_disabled(self):  # INV-06, EDGE-02
        self.enable_production()
        module_extensions.register_capability('inventory.valuation', lambda company_id: True)

        def boom(company_id, at):
            raise RuntimeError('valoración fallida')

        module_extensions.register_enable_hook('costing', boom)
        self.client.raise_request_exception = False
        self.assertEqual(self.client.post(action_url('costing', 'enable')).status_code, 500)
        self.assertNotIn('costing', self.enabled())

    def test_inventory_cannot_be_disabled_with_production(self):  # AC-04
        self.enable_production()
        response = self.client.post(action_url('inventory', 'disable'))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['dependents'], ['Producción'])
        self.assertIn('inventory', self.enabled())

    def test_production_cannot_be_disabled_with_costing(self):  # AC-04
        self.enable_production()
        module_extensions.register_capability('inventory.valuation', lambda company_id: True)
        self.client.post(action_url('costing', 'enable'))
        response = self.client.post(action_url('production', 'disable'))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['dependents'], ['Costeo'])
        self.assertTrue({'inventory', 'production', 'costing'} <= self.enabled())

    def test_open_orders_block_disabling_and_explain_how_to_resolve(self):  # AC-04, AC-06
        self.enable_production()
        blocker = Blocker('open_orders', '3 órdenes de producción abiertas',
                          'Ciérralas o cancélalas en Producción › Elaboraciones')
        module_extensions.register_disable_guard('production', lambda company_id: [blocker])
        listed = self.module('production')['disable_blockers']
        self.assertEqual(listed, [{'code': 'open_orders', 'message': blocker.message,
                                   'resolution': blocker.resolution}])
        response = self.client.post(action_url('production', 'disable'))
        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body['blockers'], listed)
        self.assertNotIn('dependents', body)
        self.assertIn(blocker.resolution, body['detail'])
        self.assertIn('production', self.enabled())

    def test_disable_without_blockers_keeps_other_modules_and_history(self):  # AC-04
        self.enable_production()
        self.assertEqual(self.client.post(action_url('production', 'disable')).status_code, 200)
        self.assertTrue({'inventory', 'sales', 'customers'} <= self.enabled())
        history = self.client.get('/api/settings/modules/history/').json()['results']
        self.assertEqual([h['new_value'] for h in history[:2]], ['Deshabilitado', 'Habilitado'])

    def test_settings_of_new_modules_are_empty_but_have_history(self):  # UI-04
        self.enable_production()
        response = self.client.get('/api/settings/production/')
        self.assertEqual((response.status_code, response.json()['settings']), (200, []))
        self.assertEqual(self.client.get('/api/settings/costing/history/').status_code, 200)
