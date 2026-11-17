"""GAS-01: cuentas elegidas por operación en los asientos automáticos (INV-03, EDGE-01..03)."""
from decimal import Decimal
from uuid import uuid4

from modules.accounting import services
from modules.accounting.infrastructure.django.models import AccountModel, JournalEntryModel
from modules.accounting.tests.test_posting_service import TODAY, PostingBase
from modules.accounting.tests.journal_support import make_account


class OverrideTests(PostingBase):
    def setUp(self):
        super().setUp()
        self.category = uuid4()
        services.set_category_account(self.company.id, self.category, self.gasto.id)
        self.configure_method('CASH', self.caja)
        self.alquiler = make_account(self.company.id, 'Alquiler', 'EXPENSE', '510002')

    def test_overrides_replace_the_configured_accounts(self):
        result = self.post('EXPENSE_RECORD', method='CASH', category_id=self.category, amount='500.00',
                           account_overrides={'EXPENSE_BY_CATEGORY': self.alquiler.id, 'MONEY': self.banco.id})
        self.assertEqual([(x.account_id, x.debit, x.credit) for x in result.entry.lines],
                         [(self.alquiler.id, Decimal('500.00'), 0), (self.banco.id, 0, Decimal('500.00'))])

    def test_overrides_make_the_configuration_unnecessary(self):
        result = self.post('EXPENSE_RECORD', category_id=uuid4(),
                           account_overrides={'EXPENSE_BY_CATEGORY': self.alquiler.id, 'MONEY': self.banco.id})
        self.assertTrue(result.created)

    def test_an_invalid_override_is_reported_and_nothing_is_posted(self):
        invalid = {'foreign': make_account(self.other.id, 'Ajena', 'EXPENSE', '510009').id,
                   'missing': uuid4(), 'wrong_class': self.cxc.id}
        for account_id in invalid.values():
            with self.assertRaises(services.PostingConfigurationMissing) as raised:
                self.post('EXPENSE_RECORD', method='CASH', category_id=self.category,
                          account_overrides={'EXPENSE_BY_CATEGORY': account_id})
            self.assertEqual(raised.exception.issues[0].code, 'account_invalid')
        AccountModel.objects.filter(pk=self.alquiler.id).update(is_active=False)
        with self.assertRaises(services.PostingConfigurationMissing):
            self.post('EXPENSE_RECORD', method='CASH', category_id=self.category,
                      account_overrides={'EXPENSE_BY_CATEGORY': self.alquiler.id})
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 0)


class ValidatePostingAccountTests(PostingBase):
    def test_accepts_a_usable_account_and_rejects_the_rest_by_role(self):
        self.assertEqual(services.validate_posting_account(self.company.id, 'EXPENSE_BY_CATEGORY',
                                                           self.gasto.id).account_id, self.gasto.id)
        self.assertEqual(services.validate_posting_account(self.company.id, 'MONEY', self.banco.id).account_id,
                         self.banco.id)
        for role, account_id in (('MONEY', self.gasto.id), ('EXPENSE_BY_CATEGORY', self.banco.id),
                                 ('MONEY', uuid4()),
                                 ('EXPENSE_BY_CATEGORY', make_account(self.other.id, 'X', 'EXPENSE', '510008').id)):
            with self.assertRaises(services.AccountValidationError):
                services.validate_posting_account(self.company.id, role, account_id)
        with self.assertRaises(services.AccountValidationError):  # Activo, pero no es Caja/Banco
            services.validate_posting_account(self.company.id, 'MONEY', self.cxc.id)
        AccountModel.objects.filter(pk=self.banco.id).update(is_active=False)
        with self.assertRaises(services.AccountValidationError):
            services.validate_posting_account(self.company.id, 'MONEY', self.banco.id)


class PostingOptionsTests(PostingBase):
    def test_without_coverage_there_is_nothing_to_show(self):
        options = services.posting_options(self.other.id, 'EXPENSE_RECORD', TODAY, method='CASH')
        self.assertEqual((options.covered, options.reason, options.defaults, options.issues, options.eligible),
                         (False, 'accounting_disabled', {}, (), {}))

    def test_defaults_issues_and_eligible_accounts(self):
        category = uuid4()
        options = services.posting_options(self.company.id, 'EXPENSE_RECORD', TODAY, method='CASH',
                                           category_id=category)
        self.assertTrue(options.covered)
        self.assertEqual({i.code for i in options.issues}, {'category_unconfigured', 'method_unconfigured'})
        self.assertEqual(options.defaults, {})
        self.assertEqual([a.id for a in options.eligible['EXPENSE_BY_CATEGORY']], [self.gasto.id])
        self.assertEqual({a.id for a in options.eligible['MONEY']}, {self.caja.id, self.banco.id})
        services.set_category_account(self.company.id, category, self.gasto.id)
        self.configure_method('CASH', self.caja)
        ready = services.posting_options(self.company.id, 'EXPENSE_RECORD', TODAY, method='CASH',
                                         category_id=category)
        self.assertEqual(ready.issues, ())
        self.assertEqual({r: a.id for r, a in ready.defaults.items()},
                         {'EXPENSE_BY_CATEGORY': self.gasto.id, 'MONEY': self.caja.id})
