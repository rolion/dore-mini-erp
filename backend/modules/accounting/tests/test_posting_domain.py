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
    get_event,
    modules_using,
    roles_of,
)


def account(account_class='ASSET', kind=None, active=True, code='1', currency='BOB'):
    value = Account.create('Cuenta', currency, kind=kind, code=code)
    value.classify(account_class) if account_class else None
    value.is_active = active
    return value


class CatalogTests(SimpleTestCase):
    def test_every_event_has_known_roles_and_a_valid_origin_kind_with_known_roles_and_a_valid_origin_kind(self):  # INV-01
        codes = [e.code for e in EVENTS]
        self.assertEqual(len(codes), len(set(codes)))
        for event in EVENTS:
            self.assertLessEqual(len(event.code), ORIGIN_KIND_MAX)
            self.assertNotEqual(event.debit_role, event.credit_role)
            self.assertIn(event.module, MODULE_LABELS)
            sides = [side for side, _ in event.lines]  # una o dos líneas de Debe y una de Haber
            self.assertIn(sides, (['DEBIT', 'CREDIT'], ['DEBIT', 'DEBIT', 'CREDIT']))
            self.assertEqual(len(set(event.role_codes)), len(event.role_codes))
        self.assertFalse(set(codes) & set(ORIGIN_KINDS))  # no choca con PRODUCT / SERVICE del libro anterior

    def test_a_module_lists_its_distinct_roles_in_order(self):
        self.assertEqual([r.code for r in roles_of('sales', SOURCE_ROLE)],
                         ['CUSTOMER_ADVANCES', 'RECEIVABLE', 'SALES_INCOME'])
        self.assertEqual([e.code for e in events_for('expenses')], ['EXPENSE_RECORD'])


class AccountProblemTests(SimpleTestCase):
    def test_valid_accounts_have_no_problem(self):  # INV-02
        self.assertIsNone(account_problem(ROLES['SALES_INCOME'], account('INCOME'), frozenset()))
        self.assertIsNone(account_problem(ROLES['MONEY'], account('ASSET', 'BANK'), frozenset()))
        self.assertIsNone(account_problem(ROLES['MONEY'], account('ASSET'), frozenset()))  # sin tipo: sirve

    def test_each_rule_has_its_own_actionable_message(self):  # INV-02
        role = ROLES['SALES_INCOME']
        self.assertIn('no existe', account_problem(role, None, frozenset()))
        self.assertIn('deshabilitada', account_problem(role, account('INCOME', active=False), frozenset()))
        self.assertIn('debe estar en BOB', account_problem(role, account('INCOME', currency='USD'), frozenset()))
        self.assertIn('clasificación', account_problem(role, account(None), frozenset()))
        self.assertIn('Ingresos', account_problem(role, account('EXPENSE'), frozenset()))
        self.assertIn('deshabilitada', account_problem(role, account('INCOME'), frozenset({'INCOME'})))
        self.assertIn('Activo', account_problem(ROLES['MONEY'], account('INCOME'), frozenset()))


class SalesEventsTests(SimpleTestCase):
    """VEN-01: anticipos de clientes y reconocimiento al entregar."""

    def test_the_advances_role_is_a_liability_without_a_fixed_account(self):
        self.assertEqual((ROLES['CUSTOMER_ADVANCES'].account_class, ROLES['CUSTOMER_ADVANCES'].source),
                         ('LIABILITY', SOURCE_ROLE))

    def test_an_advance_is_money_against_advances_and_the_delivery_has_two_debit_lines(self):
        advance, delivery = get_event('SALE_ADVANCE'), get_event('SALE_DELIVERY')
        self.assertEqual([(side, role.code) for side, role in advance.lines],
                         [('DEBIT', 'MONEY'), ('CREDIT', 'CUSTOMER_ADVANCES')])
        self.assertEqual([(side, role.code) for side, role in delivery.lines],
                         [('DEBIT', 'RECEIVABLE'), ('DEBIT', 'CUSTOMER_ADVANCES'), ('CREDIT', 'SALES_INCOME')])
        self.assertLessEqual(len(delivery.code), ORIGIN_KIND_MAX)

    def test_the_recognition_at_confirm_is_historical_hidden_but_still_known(self):
        self.assertEqual([e.code for e in events_for('sales')], ['SALE_ADVANCE', 'SALE_DELIVERY', 'SALE_PAYMENT'])
        self.assertFalse(get_event('SALE_RECOGNITION').active)
        self.assertEqual(modules_using('RECEIVABLE'), ['sales', 'receivables'])
