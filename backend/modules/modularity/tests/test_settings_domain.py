from decimal import Decimal

from django.test import SimpleTestCase

from modules.modularity.domain import modules as module_domain
from modules.modularity.domain import settings as s
from modules.sales.domain.enums import PaymentMethod, SalesChannel


class CatalogTests(SimpleTestCase):
    def test_catalog_is_coherent(self):  # INV-01
        keys = [d.key for d in s.SETTINGS_CATALOG]
        self.assertEqual(len(keys), len(set(keys)))
        for definition in s.SETTINGS_CATALOG:
            self.assertTrue(definition.key.startswith(f'{definition.module}.'))
            self.assertFalse(module_domain.definition(definition.module).is_base)
            self.assertTrue(definition.label and definition.description)
            self.assertIn(definition.kind, (s.CHOICE, s.PERCENT))  # sin tipos secretos (INV-08)
            # el valor inicial documentado es válido según su propia regla
            self.assertEqual(s.validate(definition, definition.default), definition.default)

    def test_documented_initial_values(self):  # AC-02
        initial = {d.key: d.default for d in s.SETTINGS_CATALOG}
        self.assertEqual(initial, {'sales.default_sales_channel': '', 'sales.default_payment_method': '',
                                   'sales.max_discount_percent': '100.00'})

    def test_modules_without_settings(self):
        self.assertEqual(s.settings_for('purchases'), [])
        self.assertEqual(s.settings_for('inventory'), [])

    def test_choices_match_sales_enums(self):
        self.assertEqual([v for v, _ in s.SALES_CHANNELS], [c.value for c in SalesChannel])
        self.assertEqual([v for v, _ in s.PAYMENT_METHODS], [m.value for m in PaymentMethod])


class ValidationTests(SimpleTestCase):
    def setUp(self):
        self.channel = s.BY_SETTING_KEY['sales.default_sales_channel']
        self.percent = s.BY_SETTING_KEY['sales.max_discount_percent']

    def test_choice(self):  # INV-05
        self.assertEqual(s.validate(self.channel, 'FAIR'), 'FAIR')
        self.assertEqual(s.validate(self.channel, ''), '')
        self.assertEqual(s.validate(self.channel, None), '')
        for bad in ('TELEGRAM', 'fair', 3, ['FAIR']):
            with self.assertRaises(ValueError):
                s.validate(self.channel, bad)

    def test_percent_valid(self):  # INV-05
        for raw, expected in (('50', '50.00'), (12.5, '12.50'), (Decimal('0'), '0.00'), ('100', '100.00'),
                              ('33.33', '33.33'), (' 7 ', '7.00')):
            self.assertEqual(s.validate(self.percent, raw), expected)

    def test_percent_invalid(self):  # AC-03, EDGE-08
        for bad in ('-1', '100.01', '101', '1.005', 'abc', '', None, True, 'NaN', 'Infinity'):
            with self.assertRaises(ValueError, msg=repr(bad)):
                s.validate(self.percent, bad)

    def test_validate_all_is_all_or_nothing(self):  # INV-02
        definitions = s.settings_for('sales')
        with self.assertRaises(s.SettingsValidationError) as ctx:
            s.validate_all(definitions, {'sales.default_sales_channel': 'FAIR', 'sales.max_discount_percent': '200',
                                         'sales.nope': 1})
        self.assertEqual(set(ctx.exception.errors), {'sales.max_discount_percent', 'sales.nope'})
        self.assertEqual(s.validate_all(definitions, {'sales.default_sales_channel': 'FAIR'}),
                         {'sales.default_sales_channel': 'FAIR'})

    def test_display_values(self):
        self.assertEqual(s.display(self.channel, 'STORE'), 'Venta directa')
        self.assertEqual(s.display(self.channel, ''), s.EMPTY_LABEL)
        self.assertEqual(s.display(self.percent, '100.00'), '100.00 %')
