from django.test import SimpleTestCase

from modules.customers.domain.customer import (
    EMAIL_MAX_LENGTH,
    NAME_MAX_LENGTH,
    NOTES_MAX_LENGTH,
    PHONE_MAX_LENGTH,
    Customer,
    normalize_phone,
)
from modules.customers.domain.exceptions import CustomerValidationError

CC = '591'


class NormalizePhoneTests(SimpleTestCase):
    def test_normalizable_numbers(self):  # AC-03
        for raw in ('76543210', '+591 7654-3210', '+(591) 76543210', '00591 76543210', '  +59176543210  ',
                    '765.432.10', '591 76543210', '(591) 76543210', '59176543210', '591-7654-3210'):
            self.assertEqual(normalize_phone(raw, CC), '+59176543210', raw)

    def test_digits_already_starting_with_country_code_are_prefixed(self):  # AC-03, EDGE-02
        self.assertEqual(normalize_phone('59176543210', CC), normalize_phone('76543210', CC))

    def test_short_numbers_starting_with_country_code_are_local(self):  # AC-03
        self.assertEqual(normalize_phone('59176543', CC), '+59159176543')
        self.assertEqual(normalize_phone('5917654321', CC), '+5915917654321')

    def test_uses_given_default_country_code(self):  # AC-03
        self.assertEqual(normalize_phone('3001234567', '57'), '+573001234567')

    def test_not_normalizable_is_kept_trimmed(self):  # AC-03, EDGE-08
        for raw in ('abc', '123', '  76543210 int. 5 ', '+1234567', '+1234567890123456'):
            self.assertEqual(normalize_phone(raw, CC), raw.strip(), raw)

    def test_empty_stays_empty(self):
        self.assertEqual(normalize_phone('   ', CC), '')


class CustomerCreateTests(SimpleTestCase):
    def create(self, **kwargs):
        kwargs.setdefault('name', 'Ana')
        return Customer.create(default_country_code=CC, **kwargs)

    def test_create_with_name_only_is_active_and_empty_contact(self):  # AC-01, INV-02, INV-04
        customer = self.create()
        self.assertEqual((customer.phone, customer.email, customer.notes), ('', '', ''))
        self.assertTrue(customer.active)
        self.assertIsNotNone(customer.id)

    def test_create_trims_and_normalizes(self):  # EDGE-01, AC-03
        customer = self.create(name='  Ana Pérez ', phone='7654 3210', email=' ana@x.com ', notes=' vip ')
        self.assertEqual(customer.name, 'Ana Pérez')
        self.assertEqual(customer.phone, '+59176543210')
        self.assertEqual(customer.email, 'ana@x.com')
        self.assertEqual(customer.notes, 'vip')

    def test_name_is_required(self):  # INV-01, AC-02
        for name in (None, '', '   ', 5):
            with self.assertRaises(CustomerValidationError) as ctx:
                self.create(name=name)
            self.assertIn('name', ctx.exception.errors)

    def test_limits(self):  # INV-01, INV-02, AC-02
        cases = {
            'name': 'a' * (NAME_MAX_LENGTH + 1),
            'phone': 'x' * (PHONE_MAX_LENGTH + 1),
            'email': 'a' * EMAIL_MAX_LENGTH + '@x.com',
            'notes': 'n' * (NOTES_MAX_LENGTH + 1),
        }
        for field, value in cases.items():
            with self.assertRaises(CustomerValidationError) as ctx:
                self.create(**{field: value})
            self.assertEqual(set(ctx.exception.errors), {field}, field)

    def test_max_lengths_are_accepted(self):  # INV-01, INV-02
        customer = self.create(name='a' * NAME_MAX_LENGTH, notes='n' * NOTES_MAX_LENGTH)
        self.assertEqual(len(customer.name), NAME_MAX_LENGTH)

    def test_invalid_email_formats(self):  # AC-02
        for email in ('sin-arroba', 'a@b', 'a b@c.com', '@c.com'):
            with self.assertRaises(CustomerValidationError) as ctx:
                self.create(email=email)
            self.assertIn('email', ctx.exception.errors, email)

    def test_errors_of_several_fields_are_reported_together(self):  # AC-02
        with self.assertRaises(CustomerValidationError) as ctx:
            self.create(name='', email='mal')
        self.assertEqual(set(ctx.exception.errors), {'name', 'email'})

    def test_non_text_values_are_rejected(self):
        for field in ('phone', 'email', 'notes'):
            with self.assertRaises(CustomerValidationError) as ctx:
                self.create(**{field: 5})
            self.assertIn(field, ctx.exception.errors)


class CustomerBehaviorTests(SimpleTestCase):
    def setUp(self):
        self.customer = Customer.create(name='Ana', default_country_code=CC, phone='76543210', email='a@x.com')

    def test_rename_validates(self):
        self.customer.rename('  Beatriz ')
        self.assertEqual(self.customer.name, 'Beatriz')
        with self.assertRaises(CustomerValidationError):
            self.customer.rename(' ')
        self.assertEqual(self.customer.name, 'Beatriz')

    def test_change_contact_is_atomic(self):  # AC-05
        with self.assertRaises(CustomerValidationError) as ctx:
            self.customer.change_contact(CC, phone='71111111', email='mal')
        self.assertEqual(set(ctx.exception.errors), {'email'})
        self.assertEqual(self.customer.phone, '+59176543210')
        self.customer.change_contact(CC, phone='', email='')
        self.assertEqual((self.customer.phone, self.customer.email), ('', ''))

    def test_change_contact_is_idempotent_on_normalized_phone(self):  # AC-05
        self.customer.change_contact(CC, phone=self.customer.phone, email=self.customer.email)
        self.assertEqual(self.customer.phone, '+59176543210')

    def test_change_notes(self):
        self.customer.change_notes(' hola ')
        self.assertEqual(self.customer.notes, 'hola')

    def test_activate_and_deactivate_are_idempotent(self):  # INV-04, AC-07
        self.customer.deactivate()
        self.customer.deactivate()
        self.assertFalse(self.customer.active)
        self.customer.activate()
        self.customer.activate()
        self.assertTrue(self.customer.active)
