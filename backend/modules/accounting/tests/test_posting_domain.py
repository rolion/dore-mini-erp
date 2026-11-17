"""CONT-12: catálogo fijo y reglas de cuentas por rol (INV-01, INV-02)."""
from django.test import SimpleTestCase

from modules.accounting.domain.account import Account
from modules.accounting.domain.catalog import ORIGIN_KINDS
from modules.accounting.domain.journal import ORIGIN_KIND_MAX
from modules.accounting.domain.posting import (
    EVENTS,
    MODULE_LABELS,
    ROLES,
    SOURCE_ROLE,
    account_problem,
    events_for,
    roles_of,
)


def account(account_class='ASSET', kind=None, active=True, code='1', currency='BOB'):
    value = Account.create('Cuenta', currency, kind=kind, code=code)
    value.classify(account_class) if account_class else None
    value.is_active = active
    return value


class CatalogTests(SimpleTestCase):
    def test_every_event_is_a_two_line_entry_with_known_roles_and_a_valid_origin_kind(self):  # INV-01
        codes = [e.code for e in EVENTS]
        self.assertEqual(len(codes), len(set(codes)))
        for event in EVENTS:
            self.assertLessEqual(len(event.code), ORIGIN_KIND_MAX)
            self.assertNotEqual(event.debit_role, event.credit_role)
            self.assertIn(event.module, MODULE_LABELS)
            self.assertEqual([side for side, _ in event.lines], ['DEBIT', 'CREDIT'])
        self.assertFalse(set(codes) & set(ORIGIN_KINDS))  # no choca con PRODUCT / SERVICE del libro anterior

    def test_a_module_lists_its_distinct_roles_in_order(self):
        self.assertEqual([r.code for r in roles_of('sales', SOURCE_ROLE)], ['RECEIVABLE', 'SALES_INCOME'])
        self.assertEqual([e.code for e in events_for('expenses')], ['EXPENSE_RECORD'])


class AccountProblemTests(SimpleTestCase):
    def test_valid_accounts_have_no_problem(self):  # INV-02
        self.assertIsNone(account_problem(ROLES['SALES_INCOME'], account('INCOME'), frozenset()))
        self.assertIsNone(account_problem(ROLES['MONEY'], account('ASSET', 'BANK'), frozenset()))

    def test_each_rule_has_its_own_actionable_message(self):  # INV-02
        role = ROLES['SALES_INCOME']
        self.assertIn('no existe', account_problem(role, None, frozenset()))
        self.assertIn('deshabilitada', account_problem(role, account('INCOME', active=False), frozenset()))
        self.assertIn('debe estar en BOB', account_problem(role, account('INCOME', currency='USD'), frozenset()))
        self.assertIn('clasificación', account_problem(role, account(None), frozenset()))
        self.assertIn('Ingresos', account_problem(role, account('EXPENSE'), frozenset()))
        self.assertIn('deshabilitada', account_problem(role, account('INCOME'), frozenset({'INCOME'})))
        self.assertIn('Caja, Banco', account_problem(ROLES['MONEY'], account('ASSET'), frozenset()))
