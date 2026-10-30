from django.test import SimpleTestCase

from modules.modularity.domain import modules as d


class CatalogTests(SimpleTestCase):
    def test_catalog_is_coherent(self):  # INV-06
        keys = [m.key for m in d.MODULE_CATALOG]
        self.assertEqual(len(keys), len(set(keys)))
        for module in d.MODULE_CATALOG:
            self.assertTrue(set(module.requires + module.optional) <= set(keys), module.key)
            self.assertNotIn(module.key, module.requires)
        for key in d.DEFAULT_ENABLED_KEYS:
            self.assertFalse(d.BY_KEY[key].is_base)

    def test_base_modules_have_no_dependencies(self):  # INV-01
        self.assertEqual(d.BASE_KEYS, {'access', 'catalog'})
        for key in d.BASE_KEYS:
            self.assertEqual(d.BY_KEY[key].requires, ())

    def test_required_dependencies_map(self):  # INV-06
        requires = {m.key: set(m.requires) for m in d.MODULE_CATALOG}
        self.assertEqual(requires['sales'], {'catalog'})
        self.assertEqual(requires['customers'], set())
        self.assertEqual(requires['expenses'], set())
        self.assertEqual(requires['reporting'], set())  # PB-REP-001: fuentes opcionales
        self.assertEqual(set(d.BY_KEY['reporting'].optional), {'sales', 'expenses', 'customers'})
        self.assertEqual(requires['purchases'], {'catalog', 'expenses'})
        self.assertEqual(requires['inventory'], {'catalog'})
        self.assertEqual(set(d.BY_KEY['inventory'].optional), {'sales', 'purchases'})


class RuleTests(SimpleTestCase):
    def test_enable_reports_missing_dependency_names(self):  # INV-02, AC-03
        enabled = d.effective_enabled(set())
        with self.assertRaises(d.DependencyError) as ctx:
            d.check_can_enable('purchases', enabled)
        self.assertEqual(ctx.exception.names, ['Gastos'])
        self.assertEqual(ctx.exception.kind, 'missing')

    def test_enable_ok_when_dependencies_enabled(self):
        d.check_can_enable('inventory', d.effective_enabled(set()))

    def test_cannot_disable_base(self):  # INV-01, AC-02
        with self.assertRaises(d.BaseModuleError):
            d.check_can_disable('catalog', d.effective_enabled(set()))

    def test_cannot_disable_required_module(self):  # INV-03, AC-05
        enabled = d.effective_enabled({'expenses', 'purchases'})
        with self.assertRaises(d.DependencyError) as ctx:
            d.check_can_disable('expenses', enabled)
        self.assertEqual(ctx.exception.names, ['Compras'])
        self.assertEqual(ctx.exception.kind, 'dependents')

    def test_reporting_sources_can_be_disabled_while_it_is_enabled(self):  # PB-REP-001 AC-11
        enabled = d.effective_enabled({'sales', 'expenses', 'reporting'})
        d.check_can_disable('sales', enabled)
        d.check_can_disable('expenses', enabled)
        d.check_can_enable('reporting', d.effective_enabled(set()))

    def test_unknown_key(self):  # EDGE-01
        with self.assertRaises(d.UnknownModule):
            d.definition('nope')
