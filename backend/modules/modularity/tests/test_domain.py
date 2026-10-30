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
        self.assertEqual(requires['reporting'], {'sales', 'expenses'})
        self.assertEqual(requires['purchases'], {'catalog', 'expenses'})
        self.assertEqual(requires['inventory'], {'catalog'})
        self.assertEqual(set(d.BY_KEY['inventory'].optional), {'sales', 'purchases'})
        self.assertEqual(requires['production'], {'catalog', 'inventory'})  # Compras no es obligatoria (INV-07)
        self.assertEqual(set(d.BY_KEY['production'].optional), {'purchases'})
        self.assertEqual(requires['costing'], {'production'})
        self.assertEqual(d.BY_KEY['costing'].requires_capabilities, ('inventory.valuation',))
        self.assertTrue(d.BY_KEY['costing'].records_adoption)

    def test_production_and_costing_are_off_by_default(self):  # AC-01
        self.assertFalse({'production', 'costing'} & set(d.DEFAULT_ENABLED_KEYS))


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
        enabled = d.effective_enabled({'sales', 'expenses', 'reporting'})
        with self.assertRaises(d.DependencyError) as ctx:
            d.check_can_disable('sales', enabled)
        self.assertEqual(ctx.exception.names, ['Reportes'])
        self.assertEqual(ctx.exception.kind, 'dependents')

    def test_unknown_key(self):  # EDGE-01
        with self.assertRaises(d.UnknownModule):
            d.definition('nope')


class CapabilityAndBlockerTests(SimpleTestCase):
    def test_enable_costing_without_production_reports_missing_module(self):  # INV-01, AC-02
        with self.assertRaises(d.DependencyError) as ctx:
            d.check_can_enable('costing', d.effective_enabled(set()), {'inventory.valuation'})
        self.assertEqual((ctx.exception.names, ctx.exception.kind), (['Producción'], 'missing'))

    def test_enable_costing_without_valuation_reports_capability(self):  # INV-02, AC-02
        enabled = d.effective_enabled({'inventory', 'production'})
        with self.assertRaises(d.DependencyError) as ctx:
            d.check_can_enable('costing', enabled, set())
        self.assertEqual((ctx.exception.names, ctx.exception.kind), (['Valoración de Inventario'], 'capabilities'))
        d.check_can_enable('costing', enabled, {'inventory.valuation'})

    def test_production_enables_without_purchases(self):  # INV-07, AC-01
        d.check_can_enable('production', d.effective_enabled({'inventory'}))

    def test_disable_inventory_with_production_is_blocked(self):  # INV-03, AC-04
        enabled = d.effective_enabled({'inventory', 'production'})
        with self.assertRaises(d.DependencyError) as ctx:
            d.check_can_disable('inventory', enabled)
        self.assertEqual(ctx.exception.names, ['Producción'])

    def test_disable_with_open_data_reports_blockers_and_dependents(self):  # INV-04, EDGE-05
        enabled = d.effective_enabled({'inventory', 'production', 'costing'})
        with self.assertRaises(d.DisableBlocked) as ctx:
            d.check_can_disable('production', enabled, ['orden'])
        self.assertEqual((ctx.exception.names, ctx.exception.blockers), (['Costeo'], ['orden']))
        d.check_can_disable('costing', enabled, [])
