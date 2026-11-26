"""Plantillas de módulos por tipo de empresa (INV-02, INV-03)."""
from django.test import SimpleTestCase

from modules.accounts.models import REGISTRABLE_TYPES, CompanyType
from modules.modularity.domain import company_types as types
from modules.modularity.domain.modules import BASE_KEYS, BY_KEY


class CompanyTypeTemplatesTests(SimpleTestCase):
    def test_templates_cover_exactly_the_registrable_types(self):  # paridad accounts ↔ modularity
        self.assertEqual(set(types.TEMPLATES), {t.value for t in REGISTRABLE_TYPES})
        self.assertEqual(types.GENERAL, CompanyType.GENERAL.value)

    def test_templates_only_hold_known_non_base_modules(self):
        for company_type, modules in types.TEMPLATES.items():
            self.assertTrue(set(modules) <= set(BY_KEY), company_type)
            self.assertFalse(set(modules) & BASE_KEYS, company_type)
            self.assertEqual(len(modules), len(set(modules)), company_type)

    def test_templates_satisfy_module_dependencies(self):  # INV-02
        for company_type, modules in types.TEMPLATES.items():
            enabled = set(modules) | BASE_KEYS
            for key in modules:
                self.assertEqual([k for k in BY_KEY[key].requires if k not in enabled], [], (company_type, key))

    def test_template_contents(self):  # INV-03
        self.assertEqual(set(types.template_modules('compraventa')),
                         {'customers', 'sales', 'purchases', 'inventory', 'accounting', 'expenses', 'reporting'})
        services = {'services', 'personnel', 'agenda', 'customers', 'quotations', 'receivables',
                    'accounting', 'expenses', 'reporting'}
        self.assertEqual(set(types.template_modules('servicios')), services)
        self.assertEqual(set(types.template_modules('odontologia')), services | {'dentistry'})

    def test_general_and_unknown_types_have_no_template(self):
        self.assertIsNone(types.template_modules('general'))
        self.assertIsNone(types.template_modules(''))
