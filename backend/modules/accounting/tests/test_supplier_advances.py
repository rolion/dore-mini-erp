"""COM-02 v2: anticipos a proveedores en el catálogo y la fachada (segunda línea de Haber, vista previa)."""
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.accounting import services
from modules.accounting.domain.account import AccountValidationError
from modules.accounting.domain.posting import (
    CREDIT,
    DEBIT,
    ROLES,
    get_event,
    validate_account_for_role,
)
from modules.accounting.tests.journal_support import make_account
from modules.accounting.tests.test_posting_service import TODAY, PostingBase

D = Decimal


class CatalogTests(SimpleTestCase):
    def test_the_advances_role_is_an_asset_and_the_recognition_has_a_second_credit(self):  # AC-17
        self.assertEqual(ROLES['SUPPLIER_ADVANCES'].account_class, 'ASSET')
        self.assertEqual([(side, role.code) for side, role in get_event('PURCHASE_RECOGNITION').lines],
                         [(DEBIT, 'INVENTORY'), (CREDIT, 'PAYABLE'), (CREDIT, 'SUPPLIER_ADVANCES')])
        self.assertEqual([(side, role.code) for side, role in get_event('PURCHASE_ADVANCE').lines],
                         [(DEBIT, 'SUPPLIER_ADVANCES'), (CREDIT, 'MONEY')])

    def test_the_advances_role_rejects_a_non_asset_account(self):  # AC-17
        from modules.accounting.domain.account import Account
        account = Account.create('Pasivo', 'BOB', code='210999')
        account.classify('LIABILITY')
        with self.assertRaises(AccountValidationError):
            validate_account_for_role(ROLES['SUPPLIER_ADVANCES'], account, frozenset())


class PurchaseEntriesTests(PostingBase):
    def setUp(self):
        super().setUp()
        self.inventario = make_account(self.company.id, 'Inventario', 'ASSET', '113001')
        self.proveedores = make_account(self.company.id, 'Proveedores', 'LIABILITY', '210101')
        self.anticipos_prov = make_account(self.company.id, 'Anticipos a proveedores', 'ASSET', '113101')
        services.set_role_account(self.company.id, 'INVENTORY', self.inventario.id)
        services.set_role_account(self.company.id, 'PAYABLE', self.proveedores.id)
        self.configure_method('CASH', self.caja)

    def lines(self, entry):
        return sorted((str(line.account_id), line.debit, line.credit) for line in entry.lines)

    def test_the_recognition_splits_the_credit_between_payable_and_advances(self):  # AC-16
        services.set_role_account(self.company.id, 'SUPPLIER_ADVANCES', self.anticipos_prov.id)
        posted = self.post('PURCHASE_RECOGNITION', amount='600.00', advance_applied=D('100.00'))
        self.assertEqual(self.lines(posted.entry), sorted([
            (str(self.inventario.id), D('600.00'), D('0.00')), (str(self.proveedores.id), D('0.00'), D('500.00')),
            (str(self.anticipos_prov.id), D('0.00'), D('100.00'))]))

    def test_without_advances_the_role_is_not_required_and_no_zero_line_is_created(self):  # AC-16, AC-17
        posted = self.post('PURCHASE_RECOGNITION', amount='600.00')
        self.assertEqual(len(posted.entry.lines), 2)

    def test_fully_covered_by_advances_has_no_payable_line_and_does_not_need_its_account(self):  # AC-16
        services.set_role_account(self.company.id, 'PAYABLE', None)
        services.set_role_account(self.company.id, 'SUPPLIER_ADVANCES', self.anticipos_prov.id)
        posted = self.post('PURCHASE_RECOGNITION', amount='400.00', advance_applied=D('400.00'))
        self.assertEqual(self.lines(posted.entry), sorted([
            (str(self.inventario.id), D('400.00'), D('0.00')), (str(self.anticipos_prov.id), D('0.00'), D('400.00'))]))

    def test_an_advance_greater_than_the_total_is_rejected(self):  # INV
        services.set_role_account(self.company.id, 'SUPPLIER_ADVANCES', self.anticipos_prov.id)
        with self.assertRaises(services.JournalValidationError):
            self.post('PURCHASE_RECOGNITION', amount='100.00', advance_applied=D('150.00'))

    def test_an_advance_event_needs_the_advances_account(self):  # AC-17
        with self.assertRaises(services.PostingConfigurationMissing) as caught:
            self.post('PURCHASE_ADVANCE', amount='100.00', method='CASH')
        self.assertEqual({i.role for i in caught.exception.issues}, {'SUPPLIER_ADVANCES'})

    def test_preview_returns_named_lines_without_writing(self):  # AC-18
        services.set_role_account(self.company.id, 'SUPPLIER_ADVANCES', self.anticipos_prov.id)
        before = services.journal_balances(self.company.id)
        preview = services.preview_automatic_entry(self.company.id, 'PURCHASE_ADVANCE', TODAY, D('250.00'),
                                                   method='CASH')
        self.assertTrue(preview.covered)
        self.assertEqual([(l.side, l.role, l.account_name, l.amount) for l in preview.lines], [
            ('DEBIT', 'SUPPLIER_ADVANCES', 'Anticipos a proveedores', D('250.00')),
            ('CREDIT', 'MONEY', 'Caja', D('250.00'))])
        self.assertEqual(services.journal_balances(self.company.id), before)

    def test_preview_reports_issues_and_the_lack_of_coverage(self):  # AC-18
        missing = services.preview_automatic_entry(self.company.id, 'PURCHASE_ADVANCE', TODAY, D('250.00'),
                                                   method='CASH')
        self.assertEqual((missing.lines, [i.role for i in missing.issues]), ((), ['SUPPLIER_ADVANCES']))
        uncovered = services.preview_automatic_entry(self.other.id, 'PURCHASE_ADVANCE', TODAY, D('250.00'),
                                                     method='CASH')
        self.assertEqual((uncovered.covered, uncovered.reason), (False, 'accounting_disabled'))

    def test_entries_for_returns_only_the_company_origins_in_one_query(self):  # AC-19
        services.set_role_account(self.company.id, 'SUPPLIER_ADVANCES', self.anticipos_prov.id)
        origin = uuid4()
        self.post('PURCHASE_ADVANCE', origin=origin, amount='100.00', method='CASH')
        found = services.automatic_entries_for(self.company.id, 'PURCHASE_ADVANCE', [origin, uuid4()])
        self.assertEqual(set(found), {origin})
        self.assertEqual(services.automatic_entries_for(self.other.id, 'PURCHASE_ADVANCE', [origin]), {})

    def test_the_journal_origin_exposes_the_event_label_and_module(self):  # AC-19, API-05
        from modules.accounting.api.journal_serializers import _origin
        posted = self.post('PURCHASE_RECOGNITION', amount='100.00')
        origin = _origin(posted.entry.origin_kind, posted.entry.origin_id, frozenset({'purchases'}), False)
        self.assertEqual((origin['label'], origin['module'], origin['available']),
                         ('Reconocer una compra de mercadería', 'purchases', True))
        disabled = _origin(posted.entry.origin_kind, posted.entry.origin_id, frozenset(), False)
        self.assertFalse(disabled['available'])
