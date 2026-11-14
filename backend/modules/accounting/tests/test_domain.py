"""PB-ACC-001: reglas de cuentas y mapeo (INV-01..05, 07; EDGE-05) y correspondencia de códigos (AC-08)."""
from uuid import uuid4

from django.test import SimpleTestCase

from modules.accounting.domain.account import Account, AccountValidationError, MethodMapping
from modules.accounting.domain.catalog import METHOD_CODES
from modules.receivables.domain.obligation import PaymentMethod as ReceivablesMethod
from modules.sales.domain.enums import PaymentMethod as SalesMethod


class AccountTests(SimpleTestCase):
    def test_name_is_trimmed_and_required(self):  # INV-01
        self.assertEqual(Account.create('  Caja  ', 'bob').name, 'Caja')
        for bad in ('', '   ', None, 'x' * 81):
            with self.assertRaises(AccountValidationError) as raised:
                Account.create(bad, 'BOB')
            self.assertIn('name', raised.exception.errors)

    def test_currency_must_be_known(self):  # INV-02
        self.assertEqual(Account.create('Banco', 'usd').currency, 'USD')
        with self.assertRaises(AccountValidationError) as raised:
            Account.create('Banco', 'EUR')
        self.assertIn('currency', raised.exception.errors)

    def test_only_active_bob_accounts_can_receive(self):  # INV-02, INV-04
        self.assertTrue(Account.create('Caja', 'BOB').can_receive)
        self.assertFalse(Account.create('Dólares', 'USD').can_receive)
        inactive = Account.create('Vieja', 'BOB')
        inactive.deactivate()
        self.assertFalse(inactive.can_receive)


class MethodMappingTests(SimpleTestCase):
    def test_active_method_rejects_foreign_currency_or_inactive_account(self):  # AC-02
        mapping = MethodMapping('CASH')
        with self.assertRaises(AccountValidationError):
            mapping.configure(Account.create('USD', 'USD'), True)
        inactive = Account.create('Vieja', 'BOB')
        inactive.deactivate()
        with self.assertRaises(AccountValidationError):
            mapping.configure(inactive, True)

    def test_inactive_method_may_keep_any_account(self):  # EDGE-05
        mapping = MethodMapping('CASH')
        mapping.configure(Account.create('USD', 'USD'), False)
        self.assertFalse(mapping.is_active)

    def test_completeness(self):  # INV-08
        caja = Account.create('Caja', 'BOB')
        accounts = {caja.id: caja}
        self.assertFalse(MethodMapping('CASH').is_complete(accounts))
        self.assertTrue(MethodMapping('CASH', True, caja.id).is_complete(accounts))
        self.assertTrue(MethodMapping('CASH', False, None).is_complete(accounts))
        self.assertFalse(MethodMapping('CASH', True, uuid4()).is_complete(accounts))


class CorrespondenceTests(SimpleTestCase):
    def test_codes_match_sales_and_receivables(self):  # AC-08
        self.assertEqual(set(METHOD_CODES), {m.value for m in SalesMethod})
        self.assertEqual(set(METHOD_CODES), {m.value for m in ReceivablesMethod})
