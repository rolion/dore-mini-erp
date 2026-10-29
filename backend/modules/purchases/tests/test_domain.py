from django.test import SimpleTestCase

from modules.purchases.domain.exceptions import SupplierValidationError
from modules.purchases.domain.supplier import Supplier


class SupplierCreateTests(SimpleTestCase):
    def test_name_only_creates_active_supplier_with_empty_optionals(self):  # AC-01, INV-03
        supplier = Supplier.create(name='  Distribuidora Sur  ')
        self.assertEqual(supplier.name, 'Distribuidora Sur')
        self.assertEqual((supplier.tax_id, supplier.phone, supplier.email, supplier.notes), ('', '', '', ''))
        self.assertTrue(supplier.active)

    def test_optional_fields_are_trimmed_and_none_is_empty(self):  # EDGE-01, EDGE-02
        supplier = Supplier.create(name='A', tax_id=' 123 ', phone=' 7654 ', email='   ', notes=None)
        self.assertEqual((supplier.tax_id, supplier.phone, supplier.email, supplier.notes), ('123', '7654', '', ''))

    def test_invalid_name(self):  # INV-01
        for name in (None, '', '   ', 'a' * 151, 5):
            with self.subTest(name=name), self.assertRaises(SupplierValidationError) as ctx:
                Supplier.create(name=name)
            self.assertIn('name', ctx.exception.errors)

    def test_invalid_email_formats(self):  # AC-02
        for email in ('sin-arroba', 'a@b', 'a b@c.com', 'x@' + 'a' * 250 + '.com'):
            with self.subTest(email=email), self.assertRaises(SupplierValidationError) as ctx:
                Supplier.create(name='A', email=email)
            self.assertIn('email', ctx.exception.errors)

    def test_valid_email(self):
        self.assertEqual(Supplier.create(name='A', email=' ventas@sur.com ').email, 'ventas@sur.com')

    def test_length_limits(self):  # INV-02
        for field, size in (('tax_id', 51), ('phone', 31), ('notes', 2001)):
            with self.subTest(field=field), self.assertRaises(SupplierValidationError) as ctx:
                Supplier.create(name='A', **{field: 'x' * size})
            self.assertIn(field, ctx.exception.errors)

    def test_non_text_values_are_rejected(self):  # EDGE-04
        with self.assertRaises(SupplierValidationError) as ctx:
            Supplier.create(name='A', tax_id=5, phone=7, notes=[])
        self.assertEqual(set(ctx.exception.errors), {'tax_id', 'phone', 'notes'})

    def test_errors_of_all_fields_are_reported_together(self):  # AC-02
        with self.assertRaises(SupplierValidationError) as ctx:
            Supplier.create(name='', email='mal', phone='x' * 31)
        self.assertEqual(set(ctx.exception.errors), {'name', 'email', 'phone'})
        self.assertEqual(ctx.exception.errors['name'], ['El nombre es obligatorio.'])


class SupplierBehaviorTests(SimpleTestCase):
    def setUp(self):
        self.supplier = Supplier.create(name='A', phone='111', email='a@b.com')

    def test_change_contact_is_all_or_nothing(self):
        with self.assertRaises(SupplierValidationError):
            self.supplier.change_contact('222', 'mal')
        self.assertEqual((self.supplier.phone, self.supplier.email), ('111', 'a@b.com'))
        self.supplier.change_contact('222', '')
        self.assertEqual((self.supplier.phone, self.supplier.email), ('222', ''))

    def test_rename_tax_id_and_notes(self):
        self.supplier.rename(' B ')
        self.supplier.change_tax_id(' 99 ')
        self.supplier.change_notes(' nota ')
        self.assertEqual((self.supplier.name, self.supplier.tax_id, self.supplier.notes), ('B', '99', 'nota'))
        with self.assertRaises(SupplierValidationError):
            self.supplier.rename('')
        self.assertEqual(self.supplier.name, 'B')

    def test_activate_and_deactivate_are_idempotent(self):  # AC-05, INV-03
        self.supplier.deactivate()
        self.supplier.deactivate()
        self.assertFalse(self.supplier.active)
        self.supplier.activate()
        self.supplier.activate()
        self.assertTrue(self.supplier.active)
