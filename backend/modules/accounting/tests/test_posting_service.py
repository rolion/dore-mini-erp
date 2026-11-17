"""CONT-12: fachada de asientos automáticos por evento (AC-02..AC-10; INV-01..06)."""
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from modules.accounting import services
from modules.accounting.application.use_cases import ConfigureMethod
from modules.accounting.domain.classification import Classification
from modules.accounting.infrastructure.django.models import (
    AccountModel,
    CoveragePeriodModel,
    JournalEntryModel,
    SettingsModel,
)
from modules.accounting.infrastructure.django.repositories import (
    DjangoAccountRepository,
    DjangoClassificationRepository,
    DjangoMethodMappingRepository,
)
from modules.accounting.tests.journal_support import make_account, make_period, money_account
from modules.accounting.tests.test_entries_api import enable
from modules.accounts.testing import make_company

TODAY = timezone.localdate()


class PostingBase(TestCase):
    def setUp(self):
        self.company = make_company('A')
        self.other = make_company('B')
        enable(self.company, 'accounting')
        accounts = DjangoAccountRepository(self.company.id)
        self.caja = money_account(accounts, 'Caja', '110101', 'CASH')
        self.banco = money_account(accounts, 'Banco', '110102')
        self.cxc = make_account(self.company.id, 'Cuentas por cobrar', 'ASSET', '112001')
        self.ingresos = make_account(self.company.id, 'Ingresos por ventas', 'INCOME', '410001')
        self.gasto = make_account(self.company.id, 'Gasto de luz', 'EXPENSE', '510001')
        make_period(self.company.id, 'Año', TODAY - timedelta(days=200), TODAY + timedelta(days=100))

    def configure_sales(self):
        services.set_role_account(self.company.id, 'RECEIVABLE', self.cxc.id)
        services.set_role_account(self.company.id, 'SALES_INCOME', self.ingresos.id)

    def configure_method(self, code, account):
        mappings = DjangoMethodMappingRepository(self.company.id)
        ConfigureMethod(DjangoAccountRepository(self.company.id), mappings).execute(code, account.id, True)

    def post(self, event='SALE_RECOGNITION', origin=None, amount='100.00', **extra):
        return services.post_automatic_entry(self.company.id, event, origin or uuid4(), TODAY, 'Evento',
                                             Decimal(amount), **extra)


class ReadinessTests(PostingBase):
    def test_incomplete_configuration_is_reported_before_confirming_with_an_actionable_message(self):  # AC-06
        readiness = services.check_posting_ready(self.company.id, 'SALE_RECOGNITION', TODAY)
        self.assertTrue(readiness.required)
        self.assertFalse(readiness.ready)
        self.assertEqual({i.role for i in readiness.issues}, {'RECEIVABLE', 'SALES_INCOME'})
        self.assertIn('Ventas › Configuración › Asientos automáticos', readiness.issues[0].message)
        self.assertIn('Cuentas por cobrar', readiness.issues[0].message)

    def test_complete_configuration_is_ready(self):  # AC-02
        self.configure_sales()
        self.assertTrue(services.check_posting_ready(self.company.id, 'SALE_RECOGNITION', TODAY).ready)

    def test_a_payment_event_needs_the_account_of_the_method(self):  # EDGE-02
        self.configure_sales()
        missing = services.check_posting_ready(self.company.id, 'SALE_PAYMENT', TODAY, method='CASH')
        self.assertEqual([i.code for i in missing.issues], ['method_unconfigured'])
        self.assertIn('Efectivo', missing.issues[0].message)
        self.configure_method('CASH', self.caja)
        self.assertTrue(services.check_posting_ready(self.company.id, 'SALE_PAYMENT', TODAY, method='CASH').ready)
        unknown = services.check_posting_ready(self.company.id, 'SALE_PAYMENT', TODAY, method='NOPE')
        self.assertEqual([i.code for i in unknown.issues], ['method_required'])

    def test_a_configured_account_that_was_disabled_or_reclassified_blocks_with_its_name(self):  # AC-07
        self.configure_sales()
        AccountModel.objects.filter(pk=self.cxc.id).update(is_active=False)
        issues = services.check_posting_ready(self.company.id, 'SALE_RECOGNITION', TODAY).issues
        self.assertEqual([(i.code, i.role) for i in issues], [('account_invalid', 'RECEIVABLE')])
        self.assertIn('«Cuentas por cobrar» está deshabilitada', issues[0].message)
        AccountModel.objects.filter(pk=self.cxc.id).update(is_active=True)
        AccountModel.objects.filter(pk=self.ingresos.id).update(account_class='EXPENSE')
        issues = services.check_posting_ready(self.company.id, 'SALE_RECOGNITION', TODAY).issues
        self.assertEqual([i.role for i in issues], ['SALES_INCOME'])
        self.assertIn('se requiere una cuenta de Ingresos', issues[0].message)

    def test_unknown_event_is_rejected(self):
        with self.assertRaises(services.PostingNotFound):
            services.check_posting_ready(self.company.id, 'NOPE', TODAY)


class CoverageTests(PostingBase):
    def test_with_accounting_disabled_nothing_is_required_and_nothing_is_posted(self):  # AC-08
        other_company = self.other  # sin Contabilidad habilitada
        readiness = services.check_posting_ready(other_company.id, 'SALE_RECOGNITION', TODAY)
        self.assertEqual((readiness.required, readiness.ready, readiness.reason), (False, True, 'accounting_disabled'))
        result = services.post_automatic_entry(other_company.id, 'SALE_RECOGNITION', uuid4(), TODAY, 'x',
                                               Decimal('10'))
        self.assertEqual((result.posted, result.reason, result.entry), (False, 'accounting_disabled', None))
        self.assertEqual(JournalEntryModel.objects.filter(company_id=other_company.id).count(), 0)

    def test_enabling_later_does_not_post_operations_made_before(self):  # AC-08
        self.configure_sales()
        services.coverage_status(self.company.id, TODAY)  # crea el corte de hoy
        old = TODAY - timedelta(days=10)
        result = services.post_automatic_entry(self.company.id, 'SALE_RECOGNITION', uuid4(), old, 'Antigua',
                                               Decimal('10'))
        self.assertEqual((result.posted, result.reason), (False, 'before_cutoff'))
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 0)
        readiness = services.check_posting_ready(self.company.id, 'SALE_RECOGNITION', old)
        self.assertEqual((readiness.required, readiness.reason), (False, 'before_cutoff'))

    def test_a_date_inside_a_gap_between_two_coverage_periods_is_not_posted(self):  # AC-08
        self.configure_sales()
        now = timezone.now()
        SettingsModel.objects.create(company_id=self.company.id, cutoff_date=TODAY - timedelta(days=60))
        CoveragePeriodModel.objects.create(company_id=self.company.id, started_at=now - timedelta(days=60),
                                           ended_at=now - timedelta(days=20))
        CoveragePeriodModel.objects.create(company_id=self.company.id, started_at=now - timedelta(days=5))
        in_gap = TODAY - timedelta(days=10)
        readiness = services.check_posting_ready(self.company.id, 'SALE_RECOGNITION', in_gap)
        self.assertEqual((readiness.required, readiness.reason), (False, 'in_gap'))
        result = services.post_automatic_entry(self.company.id, 'SALE_RECOGNITION', uuid4(), in_gap, 'Hueco',
                                               Decimal('10'))
        self.assertEqual((result.posted, result.reason), (False, 'in_gap'))
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 0)
        covered = services.check_posting_ready(self.company.id, 'SALE_RECOGNITION', TODAY)  # tramo vigente: sí exige
        self.assertTrue(covered.required and covered.ready)


class PostTests(PostingBase):
    def test_missing_configuration_with_coverage_is_never_skipped_silently(self):  # AC-06, INV-03
        with self.assertRaises(services.PostingConfigurationMissing) as raised:
            self.post()
        self.assertEqual({i.role for i in raised.exception.issues}, {'RECEIVABLE', 'SALES_INCOME'})
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 0)

    def test_posts_debit_and_credit_with_the_configured_accounts_and_the_event_as_origin(self):  # AC-09
        self.configure_sales()
        origin = uuid4()
        result = self.post(origin=origin, created_by=3, created_by_name='Ana')
        entry = result.entry
        self.assertEqual((result.posted, result.created, entry.source, entry.origin_kind, entry.origin_id),
                         (True, True, 'AUTOMATIC', 'SALE_RECOGNITION', origin))
        self.assertEqual([(line.account_id, line.debit, line.credit) for line in entry.lines],
                         [(self.cxc.id, Decimal('100.00'), 0), (self.ingresos.id, 0, Decimal('100.00'))])

    def test_repeating_the_event_creates_one_entry_and_a_different_one_conflicts(self):  # AC-09, INV-04
        self.configure_sales()
        origin = uuid4()
        first = self.post(origin=origin)
        again = self.post(origin=origin)
        self.assertEqual((again.created, again.entry.id), (False, first.entry.id))
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 1)
        with self.assertRaises(services.JournalConflict):
            self.post(origin=origin, amount='101.00')

    def test_invalid_amounts_do_not_leave_partial_entries(self):  # EDGE-05
        self.configure_sales()
        for amount in ('0', '-5'):
            with self.assertRaises(services.JournalValidationError):
                self.post(amount=amount)
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 0)

    def test_a_date_outside_any_open_period_is_rejected_by_the_engine(self):  # EDGE-05
        self.configure_sales()
        with self.assertRaises(services.DateOutsideFiscalPeriod):
            services.post_automatic_entry(self.company.id, 'SALE_RECOGNITION', uuid4(),
                                          TODAY + timedelta(days=400), 'Futura', Decimal('5'))

    def test_expense_uses_the_account_of_its_category_and_the_money_account_of_the_method(self):  # AC-02
        category = DjangoClassificationRepository(self.company.id).save(Classification.create('Servicios', 'EXPENSE'))
        services.set_category_account(self.company.id, category.id, self.gasto.id)
        self.configure_method('CASH', self.caja)
        result = self.post('EXPENSE_RECORD', method='CASH', classification_id=category.id)
        self.assertEqual([(line.account_id, line.debit, line.credit) for line in result.entry.lines],
                         [(self.gasto.id, Decimal('100.00'), 0), (self.caja.id, 0, Decimal('100.00'))])
        with self.assertRaises(services.PostingConfigurationMissing) as raised:
            self.post('EXPENSE_RECORD', method='CASH', classification_id=uuid4())
        self.assertEqual(raised.exception.issues[0].code, 'category_required')

    def test_a_category_without_account_is_reported_with_its_name(self):  # EDGE-03
        category = DjangoClassificationRepository(self.company.id).save(Classification.create('Servicios', 'EXPENSE'))
        self.configure_method('CASH', self.caja)
        readiness = services.check_posting_ready(self.company.id, 'EXPENSE_RECORD', TODAY, method='CASH',
                                                 classification_id=category.id)
        self.assertEqual([i.code for i in readiness.issues], ['category_unconfigured'])
        self.assertIn('«Servicios»', readiness.issues[0].message)


class HistoryTests(PostingBase):
    def test_changing_the_mapping_never_touches_a_posted_entry_and_reversal_uses_original_accounts(self):  # AC-05
        self.configure_sales()
        self.configure_method('CASH', self.banco)
        paid = self.post('SALE_PAYMENT', method='CASH')
        original = [(line.account_id, line.debit, line.credit) for line in paid.entry.lines]
        self.assertEqual(original[0][0], self.banco.id)
        self.configure_method('CASH', self.caja)  # Banco → Caja
        services_entry = services.get_journal_entry(self.company.id, paid.entry.id)
        self.assertEqual([(x.account_id, x.debit, x.credit) for x in services_entry.lines], original)
        AccountModel.objects.filter(pk=self.banco.id).update(is_active=False)  # ya ni siquiera está activa
        reversal = services.reverse_automatic_entry(self.company.id, 'SALE_PAYMENT', paid.entry.origin_id, TODAY,
                                                    'Anulación')
        self.assertTrue(reversal.created)
        self.assertEqual([(x.account_id, x.debit, x.credit) for x in reversal.entry.lines],
                         [(account, credit, debit) for account, debit, credit in original])

    def test_a_retry_after_the_configuration_changed_still_returns_the_existing_entry(self):  # AC-09, INV-06
        self.configure_sales()
        self.configure_method('CASH', self.banco)
        origin = uuid4()
        paid = self.post('SALE_PAYMENT', origin=origin, method='CASH')
        self.configure_method('CASH', self.caja)  # Banco → Caja después de contabilizar
        services.set_role_account(self.company.id, 'RECEIVABLE', None)  # y se quita una cuenta
        again = self.post('SALE_PAYMENT', origin=origin, method='CASH')
        self.assertEqual((again.posted, again.created, again.entry.id), (True, False, paid.entry.id))
        self.assertEqual([line.account_id for line in again.entry.lines], [self.banco.id, self.cxc.id])
        with self.assertRaises(services.JournalConflict):  # distinto importe sigue siendo conflicto
            self.post('SALE_PAYMENT', origin=origin, method='CASH', amount='99.00')
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 1)

    def test_reversing_an_event_that_was_never_posted_returns_nothing(self):  # AC-08
        self.assertIsNone(services.reverse_automatic_entry(self.company.id, 'SALE_RECOGNITION', uuid4(), TODAY, 'x'))

    def test_a_second_reversal_returns_the_existing_one(self):  # INV-04
        self.configure_sales()
        entry = self.post().entry
        first = services.reverse_automatic_entry(self.company.id, 'SALE_RECOGNITION', entry.origin_id, TODAY, 'x')
        again = services.reverse_automatic_entry(self.company.id, 'SALE_RECOGNITION', entry.origin_id, TODAY, 'x')
        self.assertEqual((first.created, again.created, again.entry.id), (True, False, first.entry.id))


class AssignmentTests(PostingBase):
    def assertRejected(self, role, account_id, text):
        with self.assertRaises(services.AccountValidationError) as raised:
            services.set_role_account(self.company.id, role, account_id)
        self.assertIn(text, raised.exception.errors['account_id'][0])

    def test_wrong_class_foreign_inactive_or_missing_accounts_are_rejected(self):  # AC-03
        self.assertRejected('SALES_INCOME', self.gasto.id, 'se requiere una cuenta de Ingresos')
        foreign = make_account(self.other.id, 'Ingresos ajenos', 'INCOME', '410001')
        self.assertRejected('SALES_INCOME', foreign.id, 'no existe en esta empresa')
        self.assertRejected('SALES_INCOME', uuid4(), 'no existe en esta empresa')
        AccountModel.objects.filter(pk=self.ingresos.id).update(is_active=False)
        self.assertRejected('SALES_INCOME', self.ingresos.id, 'deshabilitada')
        self.assertEqual(services.describe_posting_config(self.company.id, 'sales').config.roles[1].account, None)

    def test_a_disabled_class_cannot_be_used_for_new_assignments(self):  # AC-03
        from modules.accounting.infrastructure.django.repositories import DjangoAccountClassRepository
        DjangoAccountClassRepository(self.company.id).set_enabled('INCOME', False)
        self.assertRejected('SALES_INCOME', self.ingresos.id, 'deshabilitada')

    def test_a_method_account_must_be_an_active_bob_asset_whatever_its_type(self):  # AC-04
        self.configure_method('CASH', self.cxc)  # Activo sin tipo Caja/Banco: sirve
        for account in (self.ingresos, self.gasto):
            with self.assertRaises(services.AccountValidationError):
                self.configure_method('QR', account)

    def test_roles_with_other_source_or_unknown_are_not_found(self):
        for role in ('NOPE', 'MONEY', 'EXPENSE_BY_CATEGORY'):
            with self.assertRaises(services.PostingNotFound):
                services.set_role_account(self.company.id, role, None)

    def test_clearing_removes_the_assignment(self):  # AC-02
        self.configure_sales()
        services.set_role_account(self.company.id, 'RECEIVABLE', None)
        roles = {r.role: r for r in services.describe_posting_config(self.company.id, 'sales').config.roles}
        self.assertIsNone(roles['RECEIVABLE'].account)
        self.assertEqual(roles['SALES_INCOME'].account.id, self.ingresos.id)

    def test_category_must_be_an_expense_classification_of_the_company(self):  # AC-03
        income = DjangoClassificationRepository(self.company.id).save(Classification.create('Ventas', 'INCOME'))
        with self.assertRaises(services.AccountValidationError):
            services.set_category_account(self.company.id, income.id, self.gasto.id)
        theirs = DjangoClassificationRepository(self.other.id).save(Classification.create('Otra', 'EXPENSE'))
        from modules.accounting.domain.classification import ClassificationNotFound
        with self.assertRaises(ClassificationNotFound):
            services.set_category_account(self.company.id, theirs.id, self.gasto.id)
        mine = DjangoClassificationRepository(self.company.id).save(Classification.create('Luz', 'EXPENSE'))
        with self.assertRaises(services.AccountValidationError):
            services.set_category_account(self.company.id, mine.id, self.ingresos.id)


class DescribeTests(PostingBase):
    def test_each_module_sees_only_its_events_with_a_debit_credit_preview(self):  # AC-01
        view = services.describe_posting_config(self.company.id, 'sales')
        self.assertTrue(view.accounting_enabled)
        self.assertEqual([e.code for e in view.config.events], ['SALE_RECOGNITION', 'SALE_PAYMENT'])
        self.assertEqual([(line.side, line.role, line.status) for line in view.config.events[0].preview],
                         [('DEBIT', 'RECEIVABLE', 'missing'), ('CREDIT', 'SALES_INCOME', 'missing')])
        self.assertEqual([line.status for line in view.config.events[1].preview], ['by_method', 'missing'])
        self.assertEqual(len(view.config.methods), 5)
        self.assertFalse(view.config.ready)
        self.assertEqual([e.code for e in services.describe_posting_config(self.company.id, 'inventory').config.events],
                         ['INVENTORY_SALE_COST'])
        with self.assertRaises(services.PostingNotFound):
            services.describe_posting_config(self.company.id, 'customers')

    def test_a_shared_role_tells_which_other_modules_use_it(self):  # EDGE-01
        roles = {r.role: r for r in services.describe_posting_config(self.company.id, 'inventory').config.roles}
        self.assertEqual(roles['INVENTORY'].shared_with, ('purchases',))

    def test_module_is_ready_only_with_every_active_method_and_category_configured(self):
        self.configure_sales()
        self.assertFalse(services.describe_posting_config(self.company.id, 'sales').config.ready)
        mappings = DjangoMethodMappingRepository(self.company.id)
        accounts = DjangoAccountRepository(self.company.id)
        for code in ('CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'):
            ConfigureMethod(accounts, mappings).execute(code, self.banco.id, True)
        self.assertTrue(services.describe_posting_config(self.company.id, 'sales').config.ready)

    def test_reading_does_not_scale_queries_with_methods_or_categories(self):  # NFR
        repo = DjangoClassificationRepository(self.company.id)
        for index in range(6):
            repo.save(Classification.create(f'Categoría {index}', 'EXPENSE'))
        with CaptureQueriesContext(connection) as queries:
            services.describe_posting_config(self.company.id, 'expenses')
        self.assertLessEqual(len(queries), 8)

    def test_company_isolation(self):  # AC-10
        self.configure_sales()
        theirs = services.describe_posting_config(self.other.id, 'sales').config
        self.assertTrue(all(r.account is None for r in theirs.roles))
        with self.assertRaises(services.AccountValidationError):
            services.set_role_account(self.other.id, 'RECEIVABLE', self.cxc.id)
