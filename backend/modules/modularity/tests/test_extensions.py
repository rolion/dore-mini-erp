from datetime import datetime, timezone
from uuid import uuid4

from django.test import SimpleTestCase

from modules.modularity.application.use_cases import DisableModule, EnableModule, ListModules
from modules.modularity.domain import modules as d
from shared import module_extensions
from shared.module_extensions import Blocker


class FakeRepository:
    def __init__(self, keys):
        self.keys = set(keys)
        self.dates = {k: datetime(2026, 10, 1, tzinfo=timezone.utc) for k in keys}
        self.clock = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)

    def enabled_keys(self):
        return set(self.keys)

    def enabled_at(self):
        return dict(self.dates)

    def enable(self, key):
        self.keys.add(key)
        self.dates[key] = self.clock

    def disable(self, key):
        self.keys.discard(key)
        self.dates.pop(key, None)


class FakeExtensions:
    def __init__(self, capabilities=(), blockers=None, fail_hook=False):
        self.capabilities = set(capabilities)
        self.blockers = blockers or {}
        self.hooks = []
        self.fail_hook = fail_hook

    def available_capabilities(self, keys):
        return {k for k in keys if k in self.capabilities}

    def disable_blockers(self, module_key):
        return self.blockers.get(module_key, [])

    def on_enabled(self, module_key, adopted_at):
        if self.fail_hook:
            raise RuntimeError('valoración fallida')
        self.hooks.append((module_key, adopted_at))


class UnexpectedGuardCall(FakeExtensions):
    def disable_blockers(self, module_key):
        if module_key == 'production':
            raise AssertionError('las guardas del módulo deshabilitado no deben consultarse')
        return []


def view(views, key):
    return next(v for v in views if v.definition.key == key)


class EnableTests(SimpleTestCase):
    def test_production_enables_without_costing_or_purchases(self):  # AC-01
        repo = FakeRepository({'inventory'})
        views = EnableModule(repo, None, FakeExtensions()).execute('production')
        self.assertTrue(view(views, 'production').enabled)
        self.assertFalse(view(views, 'costing').enabled)
        self.assertNotIn('purchases', repo.keys)

    def test_costing_requires_valuation_capability(self):  # AC-02
        repo = FakeRepository({'inventory', 'production'})
        with self.assertRaises(d.DependencyError) as ctx:
            EnableModule(repo, None, FakeExtensions()).execute('costing')
        self.assertEqual((ctx.exception.kind, ctx.exception.names), ('capabilities', ['Valoración de Inventario']))
        self.assertNotIn('costing', repo.keys)

    def test_costing_records_adoption_and_runs_hook_once(self):  # AC-05, EDGE-01
        repo, ext = FakeRepository({'inventory', 'production'}), FakeExtensions({'inventory.valuation'})
        views = EnableModule(repo, None, ext).execute('costing')
        self.assertEqual(view(views, 'costing').adopted_at, repo.clock)
        self.assertEqual(ext.hooks, [('costing', repo.clock)])
        EnableModule(repo, None, ext).execute('costing')
        self.assertEqual(len(ext.hooks), 1)

    def test_production_does_not_run_adoption_hook(self):  # AC-05
        ext = FakeExtensions()
        EnableModule(FakeRepository({'inventory'}), None, ext).execute('production')
        self.assertEqual(ext.hooks, [])

    def test_hook_failure_propagates_so_the_transaction_rolls_back(self):  # INV-06, EDGE-02
        repo = FakeRepository({'inventory', 'production'})
        with self.assertRaises(RuntimeError):
            EnableModule(repo, None, FakeExtensions({'inventory.valuation'}, fail_hook=True)).execute('costing')

    def test_listing_reports_capability_state_without_provider(self):  # AC-03, EDGE-04
        repo = FakeRepository({'inventory', 'production', 'costing'})
        costing = view(ListModules(repo).execute(), 'costing')
        self.assertEqual(costing.missing_capabilities, ['Valoración de Inventario'])
        self.assertEqual(costing.capabilities, [('inventory.valuation', 'Valoración de Inventario', False)])

    def test_adoption_date_only_for_modules_that_record_it(self):  # AC-05
        views = ListModules(FakeRepository({'inventory', 'production', 'costing'}),
                            FakeExtensions({'inventory.valuation'})).execute()
        self.assertIsNotNone(view(views, 'costing').adopted_at)
        self.assertIsNone(view(views, 'production').adopted_at)

    def test_reenabling_costing_sets_a_new_adoption_date(self):  # INV-05, EDGE-06
        repo, ext = FakeRepository({'inventory', 'production'}), FakeExtensions({'inventory.valuation'})
        EnableModule(repo, None, ext).execute('costing')
        DisableModule(repo, None, ext).execute('costing')
        repo.clock = datetime(2026, 11, 15, tzinfo=timezone.utc)
        views = EnableModule(repo, None, ext).execute('costing')
        self.assertEqual(view(views, 'costing').adopted_at, repo.clock)
        self.assertEqual(len(ext.hooks), 2)


class DisableTests(SimpleTestCase):
    def test_inventory_blocked_while_production_is_enabled(self):  # AC-04
        repo = FakeRepository({'inventory', 'production'})
        with self.assertRaises(d.DependencyError) as ctx:
            DisableModule(repo, None, FakeExtensions()).execute('inventory')
        self.assertEqual(ctx.exception.names, ['Producción'])
        self.assertIn('inventory', repo.keys)

    def test_production_blocked_by_costing_and_open_orders(self):  # AC-04, EDGE-05
        blocker = Blocker('open_orders', '3 órdenes abiertas', 'Ciérralas en Elaboraciones')
        repo = FakeRepository({'inventory', 'production', 'costing'})
        with self.assertRaises(d.DisableBlocked) as ctx:
            DisableModule(repo, None, FakeExtensions(blockers={'production': [blocker]})).execute('production')
        self.assertEqual((ctx.exception.names, ctx.exception.blockers), (['Costeo'], [blocker]))
        self.assertEqual(repo.keys, {'inventory', 'production', 'costing'})

    def test_open_orders_block_even_without_dependents(self):  # INV-04
        blocker = Blocker('open_orders', '2 órdenes abiertas', 'Ciérralas')
        repo = FakeRepository({'inventory', 'production'})
        with self.assertRaises(d.DisableBlocked):
            DisableModule(repo, None, FakeExtensions(blockers={'production': [blocker]})).execute('production')

    def test_disable_does_not_touch_other_modules(self):  # AC-04
        repo = FakeRepository({'inventory', 'production', 'sales'})
        DisableModule(repo, None, FakeExtensions()).execute('production')
        self.assertEqual(repo.keys, {'inventory', 'sales'})

    def test_disabling_an_already_disabled_module_skips_guards(self):  # EDGE-01
        DisableModule(FakeRepository({'inventory'}), None, UnexpectedGuardCall()).execute('production')

    def test_listing_exposes_blockers_for_enabled_modules(self):  # AC-06
        blocker = Blocker('open_orders', '2 órdenes abiertas', 'Ciérralas')
        views = ListModules(FakeRepository({'inventory', 'production'}),
                            FakeExtensions(blockers={'production': [blocker]})).execute()
        self.assertEqual(view(views, 'production').blockers, [blocker])
        self.assertEqual(view(views, 'inventory').blockers, [])


class SharedPortTests(SimpleTestCase):
    def setUp(self):
        module_extensions.reset()
        self.addCleanup(module_extensions.reset)
        self.company, self.other = uuid4(), uuid4()

    def test_capability_unavailable_without_provider(self):  # INV-02
        self.assertFalse(module_extensions.capability_available(self.company, 'inventory.valuation'))

    def test_capability_is_per_company(self):  # EDGE-03
        module_extensions.register_capability('inventory.valuation', lambda company_id: company_id == self.company)
        self.assertTrue(module_extensions.capability_available(self.company, 'inventory.valuation'))
        self.assertFalse(module_extensions.capability_available(self.other, 'inventory.valuation'))

    def test_guards_and_hooks_are_registered_per_module(self):
        blocker = Blocker('x', 'm', 'r')
        module_extensions.register_disable_guard('production', lambda company_id: [blocker])
        calls = []
        module_extensions.register_enable_hook('costing', lambda company_id, at: calls.append((company_id, at)))
        at = datetime(2026, 10, 30, tzinfo=timezone.utc)
        self.assertEqual(module_extensions.disable_blockers(self.company, 'production'), [blocker])
        self.assertEqual(module_extensions.disable_blockers(self.company, 'costing'), [])
        module_extensions.run_enable_hooks(self.company, 'costing', at)
        self.assertEqual(calls, [(self.company, at)])
