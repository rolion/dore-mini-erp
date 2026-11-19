"""Configuración contable y de módulos por defecto: alta de empresa y copia a empresas existentes."""
import json
import re
from datetime import date
from io import StringIO
from unittest import mock

from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.test import TestCase
from rest_framework.test import APITestCase

from modules.accounting.infrastructure.django.models import (
    AccountModel,
    ClassificationModel,
    CoveragePeriodModel,
    FiscalPeriodModel,
    MethodMappingModel,
    PostingAccountModel,
    SettingsModel,
)
from modules.accounts.models import Company
from modules.expenses.infrastructure.django.models import ExpenseCategoryModel
from modules.inventory.infrastructure.django.models import WarehouseModel
from modules.modularity.infrastructure.django.models import CompanyModuleModel, CompanySettingModel
from modules.purchases.infrastructure.django.models import SettingsModel as PurchasesSettingsModel
from shared import company_defaults

SNAPSHOT = company_defaults.load_snapshot()


def run(*args):
    out = StringIO()
    call_command(*args, stdout=out)
    return out.getvalue()


class SnapshotTests(TestCase):
    def test_snapshot_has_no_uuids_or_cross_company_ids(self):  # AC-08, INV-01
        text = json.dumps(SNAPSHOT)
        self.assertIsNone(re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}', text))

    def test_invalid_snapshot_is_rejected(self):  # edge: snapshot inválido
        with self.assertRaises(company_defaults.DefaultsError):
            company_defaults.apply_all(Company.objects.create(name='X').id, {'version': 99})


class RegisterSeedsDefaultsTests(APITestCase):
    payload = {
        'company_name': 'Nueva SRL', 'username': 'nuevo', 'first_name': 'Ana', 'last_name': 'Paz',
        'email': 'ana@example.com', 'password': 'Cl4ve-segura-2026',
    }

    def setUp(self):
        cache.clear()

    def register(self, **overrides):
        response = self.client.post('/api/auth/register/', {**self.payload, **overrides}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return Company.objects.get(name=overrides.get('company_name', self.payload['company_name']))

    def test_new_company_gets_chart_mappings_and_classifications(self):  # AC-01, AC-02, AC-03
        company = self.register()
        accounts = AccountModel.objects.filter(company_id=company.id)
        self.assertEqual(accounts.count(), len(SNAPSHOT['accounting']['accounts']))
        self.assertEqual(sorted(accounts.values_list('code', flat=True)),
                         sorted(a['code'] for a in SNAPSHOT['accounting']['accounts']))
        self.assertEqual(MethodMappingModel.objects.filter(company_id=company.id).count(), 5)
        self.assertEqual(ClassificationModel.objects.filter(company_id=company.id).count(),
                         len(SNAPSHOT['accounting']['classifications']))
        roles = PostingAccountModel.objects.filter(company_id=company.id, scope='ROLE')
        self.assertEqual(roles.count(), len(SNAPSHOT['accounting_posting']['roles']))

    def test_category_posting_accounts_point_to_the_new_company_categories(self):  # AC-02
        company = self.register()
        category_ids = {str(c.id) for c in ExpenseCategoryModel.objects.filter(company_id=company.id)}
        keys = set(PostingAccountModel.objects.filter(company_id=company.id, scope='CATEGORY')
                   .values_list('key', flat=True))
        self.assertEqual(len(keys), len(SNAPSHOT['accounting_posting']['categories']))
        self.assertTrue(keys <= category_ids)

    def test_purchases_setting_points_to_the_right_classification(self):  # AC-03
        company = self.register()
        wanted = SNAPSHOT['purchases']['payment_classification']
        row = PurchasesSettingsModel.objects.get(company_id=company.id)
        classification = ClassificationModel.objects.get(pk=row.payment_classification_id)
        self.assertEqual((classification.company_id, classification.name, classification.direction),
                         (company.id, wanted['name'], wanted['direction']))

    def test_modules_cutoff_period_and_coverage(self):  # AC-04
        company = self.register()
        enabled = set(CompanyModuleModel.objects.filter(company_id=company.id).values_list('module_key', flat=True))
        self.assertEqual(enabled, set(SNAPSHOT['modularity']['modules']))
        self.assertEqual(len(enabled), 14)
        today = date.today()
        self.assertEqual(SettingsModel.objects.get(company_id=company.id).cutoff_date, today)
        period = FiscalPeriodModel.objects.get(company_id=company.id)
        self.assertEqual((period.name, period.start_date, period.end_date, period.status),
                         (str(today.year), date(today.year, 1, 1), date(today.year, 12, 31), 'OPEN'))
        self.assertTrue(CoveragePeriodModel.objects.filter(company_id=company.id, ended_at__isnull=True).exists())
        self.assertTrue(all(a.opening_balance == 0 for a in AccountModel.objects.filter(company_id=company.id)))

    def test_settings_categories_and_warehouse(self):  # AC-05
        company = self.register()
        values = dict(CompanySettingModel.objects.filter(company_id=company.id).values_list('setting_key', 'value'))
        self.assertEqual(values, SNAPSHOT['modularity']['settings'])
        self.assertEqual(ExpenseCategoryModel.objects.filter(company_id=company.id).count(), 4)
        self.assertTrue(WarehouseModel.objects.get(company_id=company.id, is_default=True).active)

    def test_two_registrations_do_not_mix_and_old_companies_are_untouched(self):  # AC-06
        legacy = Company.objects.create(name='Antigua SRL')
        first = self.register()
        second = self.register(company_name='Otra SRL', username='otro', email='o@example.com')
        for model in (AccountModel, ClassificationModel, PostingAccountModel):
            self.assertEqual(model.objects.filter(company_id=first.id).count(),
                             model.objects.filter(company_id=second.id).count())
        self.assertFalse(set(AccountModel.objects.filter(company_id=first.id).values_list('id', flat=True))
                         & set(AccountModel.objects.filter(company_id=second.id).values_list('id', flat=True)))
        self.assertFalse(AccountModel.objects.filter(company_id=legacy.id).exists())

    def test_failure_in_a_section_rolls_back_the_company(self):  # AC-09, INV-05
        failing = company_defaults.Section('expenses', 30, lambda *_: {},
                                           mock.Mock(side_effect=company_defaults.DefaultsError('boom')))
        with mock.patch.dict(company_defaults._sections, {'expenses': failing}):
            with self.assertRaises(company_defaults.DefaultsError):
                self.client.post('/api/auth/register/', self.payload, format='json')
        self.assertFalse(Company.objects.filter(name='Nueva SRL').exists())
        self.assertFalse(AccountModel.objects.exists())


class CopyCommandTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Vacía SRL')

    def counts(self, company):
        return (AccountModel.objects.filter(company_id=company.id).count(),
                PostingAccountModel.objects.filter(company_id=company.id).count(),
                CompanyModuleModel.objects.filter(company_id=company.id).count())

    def test_copy_to_empty_company_equals_registration_result(self):  # AC-07
        run('copy_company_defaults', '--company', 'vacía srl')
        self.assertEqual(self.counts(self.company), (20, 10, 14))
        self.assertEqual(company_defaults.export_all(self.company.id), {**SNAPSHOT})  # AC-08 ida y vuelta

    def test_copy_is_idempotent(self):  # INV-02
        run('copy_company_defaults', '--company', str(self.company.id))
        before = self.counts(self.company)
        out = run('copy_company_defaults', '--company', str(self.company.id))
        self.assertEqual(self.counts(self.company), before)
        self.assertNotRegex(out, r'[1-9]\d* creados')

    def test_copy_completes_only_what_is_missing(self):  # AC-07, INV-03
        AccountModel.objects.create(company_id=self.company.id, code='1102', name='Mi banco', currency='BOB',
                                    account_class='ASSET', kind='BANK')
        CompanySettingModel.objects.create(company_id=self.company.id, setting_key='sales.default_payment_method',
                                           value='CASH')
        run('copy_company_defaults', '--company', 'Vacía SRL')
        self.assertEqual(AccountModel.objects.get(company_id=self.company.id, code='1102').name, 'Mi banco')
        self.assertEqual(AccountModel.objects.filter(company_id=self.company.id).count(), 20)
        self.assertEqual(CompanySettingModel.objects.get(
            company_id=self.company.id, setting_key='sales.default_payment_method').value, 'CASH')

    def test_dry_run_writes_nothing(self):  # AC-07
        out = run('copy_company_defaults', '--company', 'Vacía SRL', '--dry-run')
        self.assertIn('Simulación', out)
        self.assertEqual(self.counts(self.company), (0, 0, 0))

    def test_unknown_company_fails_clearly(self):  # AC-07
        with self.assertRaisesRegex(CommandError, 'No existe la empresa'):
            run('copy_company_defaults', '--company', 'No existe')

    def test_broken_snapshot_reference_writes_nothing(self):  # edge: referencia inexistente
        bad = json.loads(json.dumps(SNAPSHOT))
        bad['accounting']['method_mappings'][0]['account_code'] = '9999'
        with self.assertRaises(company_defaults.DefaultsError):
            company_defaults.apply_all(self.company.id, bad)
        self.assertEqual(self.counts(self.company), (0, 0, 0))

    def test_export_command_writes_snapshot_without_uuids(self):  # AC-08
        run('copy_company_defaults', '--company', 'Vacía SRL')
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'out.json'
            run('export_company_defaults', '--company', 'Vacía SRL', '--output', str(target))
            self.assertEqual(json.loads(target.read_text(encoding='utf-8')), SNAPSHOT)
