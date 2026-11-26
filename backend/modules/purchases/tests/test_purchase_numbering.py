"""Numeración correlativa de compras por período fiscal con BD real (TASK-numeracion-correlativa-compras)."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.test import TestCase

from modules.accounting.infrastructure.django.models import FiscalPeriodModel
from modules.accounts.testing import make_company
from modules.purchases.application.purchase_commands import CancelPurchase, ConfirmPurchase
from modules.purchases.domain.exceptions import PurchaseNumberingRejected
from modules.purchases.domain.purchase import ItemDraft, Purchase, PurchaseNumber
from modules.purchases.infrastructure.adapters import PurchaseNumberingAdapter, _period_suffix
from modules.purchases.infrastructure.django.models import PurchaseModel, PurchaseNumberCounterModel, SupplierModel
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository
from modules.purchases.infrastructure.django.repositories import DjangoSupplierRepository
from modules.purchases.tests.test_purchase_api import LIST_URL, PurchaseApiTestCase, detail_url


def make_period(company, name, start, end, status='OPEN'):
    return FiscalPeriodModel.objects.create(
        company_id=company.id, name=name, start_date=start, end_date=end, status=status)


def make_purchase(company, purchase_date, confirm=True):
    from django.utils import timezone
    supplier = SupplierModel.objects.filter(company_id=company.id).first() or SupplierModel.objects.create(
        company_id=company.id, name='Sur')
    repository = DjangoPurchaseRepository(company.id)
    purchase = repository.save(Purchase.create(
        supplier_id=supplier.id, purchase_date=purchase_date,
        items=[ItemDraft(uuid4(), '2', '10.00', product_name='Harina')]))
    if confirm:
        with transaction.atomic():
            purchase = ConfirmPurchase(repository, DjangoSupplierRepository(company.id),
                                       PurchaseNumberingAdapter(company.id)).execute(purchase.id, timezone.now())
    return purchase


def confirm_use_case(company):
    return ConfirmPurchase(DjangoPurchaseRepository(company.id), DjangoSupplierRepository(company.id),
                           PurchaseNumberingAdapter(company.id))


class SeriesTests(TestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.p2026 = make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        self.p2027 = make_period(self.company, 'Gestión 2027', date(2027, 1, 1), date(2027, 12, 31))

    def test_numbers_are_consecutive_and_restart_in_each_period(self):  # AC-01
        a = make_purchase(self.company, date(2026, 3, 1))
        b = make_purchase(self.company, date(2026, 9, 1))
        c = make_purchase(self.company, date(2027, 1, 5))
        d = make_purchase(self.company, date(2026, 12, 31))
        self.assertEqual([p.reference for p in (a, b, c, d)], ['NC-000001', 'NC-000002', 'NC-000001', 'NC-000003'])
        self.assertEqual((a.number.period_id, c.number.period_id), (self.p2026.id, self.p2027.id))

    def test_the_period_is_the_one_of_the_purchase_date(self):  # AC-04, INV-04
        purchase = make_purchase(self.company, date(2026, 12, 30))  # se confirma «hoy», de otro período
        self.assertEqual((purchase.number.period_name, purchase.reference), ('Gestión 2026', 'NC-000001'))

    def test_each_company_has_its_own_series(self):  # AC-01, INV-05
        other = make_company('Empresa B')
        make_period(other, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        make_purchase(self.company, date(2026, 3, 1))
        make_purchase(self.company, date(2026, 3, 2))
        self.assertEqual(make_purchase(other, date(2026, 3, 1)).reference, 'NC-000001')

    def test_the_purchases_series_is_independent_of_the_sales_series(self):  # AC-01, INV-05
        from modules.sales.infrastructure.django.models import OrderNumberCounterModel
        OrderNumberCounterModel.objects.create(
            company_id=self.company.id, fiscal_period_id=self.p2026.id, last_number=40)
        self.assertEqual(make_purchase(self.company, date(2026, 3, 1)).reference, 'NC-000001')

    def test_a_draft_does_not_consume_a_number(self):  # AC-02
        make_purchase(self.company, date(2026, 3, 1), confirm=False)
        make_purchase(self.company, date(2026, 3, 2), confirm=False)
        self.assertEqual(make_purchase(self.company, date(2026, 3, 3)).reference, 'NC-000001')

    def test_a_cancelled_purchase_keeps_its_number_and_it_is_not_reused(self):  # AC-03
        from django.utils import timezone
        first = make_purchase(self.company, date(2026, 3, 1))
        repository = DjangoPurchaseRepository(self.company.id)
        with transaction.atomic():
            CancelPurchase(repository).execute(first.id, 'error', timezone.now())
        self.assertEqual(repository.get(first.id).reference, 'NC-000001')
        self.assertEqual(make_purchase(self.company, date(2026, 3, 2)).reference, 'NC-000002')

    def test_the_period_name_is_a_snapshot(self):  # EDGE-03
        purchase = make_purchase(self.company, date(2026, 3, 1))
        FiscalPeriodModel.objects.filter(pk=self.p2026.id).update(name='Renombrado')
        self.assertEqual(DjangoPurchaseRepository(self.company.id).get(purchase.id).number.period_name, 'Gestión 2026')

    def test_no_period_blocks_and_leaves_the_counter_untouched(self):  # AC-05
        purchase = make_purchase(self.company, date(2028, 1, 1), confirm=False)
        with self.assertRaises(PurchaseNumberingRejected) as caught, transaction.atomic():
            from django.utils import timezone
            confirm_use_case(self.company).execute(purchase.id, timezone.now())
        self.assertEqual(caught.exception.code, 'fiscal_period_missing')
        self.assertEqual(DjangoPurchaseRepository(self.company.id).get(purchase.id).status.value, 'draft')
        self.assertFalse(PurchaseNumberCounterModel.objects.filter(company_id=self.company.id).exists())

    def test_a_closed_period_blocks_and_a_reopened_one_continues_the_series(self):  # AC-06, EDGE-05
        from django.utils import timezone
        make_purchase(self.company, date(2026, 3, 1))
        FiscalPeriodModel.objects.filter(pk=self.p2026.id).update(status='CLOSED')
        purchase = make_purchase(self.company, date(2026, 3, 2), confirm=False)
        with self.assertRaises(PurchaseNumberingRejected) as caught, transaction.atomic():
            confirm_use_case(self.company).execute(purchase.id, timezone.now())
        self.assertEqual((caught.exception.code, caught.exception.extra), ('fiscal_period_closed',
                                                                           {'period': 'Gestión 2026'}))
        FiscalPeriodModel.objects.filter(pk=self.p2026.id).update(status='OPEN')
        with transaction.atomic():
            confirmed = confirm_use_case(self.company).execute(purchase.id, timezone.now())
        self.assertEqual(confirmed.reference, 'NC-000002')

    def test_a_failure_after_numbering_rolls_the_counter_back(self):  # AC-09, INV-02
        from django.utils import timezone
        purchase = make_purchase(self.company, date(2026, 3, 1), confirm=False)
        with self.assertRaises(RuntimeError), transaction.atomic():
            confirm_use_case(self.company).execute(purchase.id, timezone.now())
            raise RuntimeError('falla posterior a numerar')
        self.assertEqual(DjangoPurchaseRepository(self.company.id).get(purchase.id).status.value, 'draft')
        self.assertEqual(make_purchase(self.company, date(2026, 3, 2)).reference, 'NC-000001')

    def test_the_database_rejects_a_duplicate_number(self):  # INV-01
        purchase = make_purchase(self.company, date(2026, 3, 1))
        twin = make_purchase(self.company, date(2026, 3, 2), confirm=False)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PurchaseModel.objects.filter(pk=twin.id).update(
                fiscal_period_id=purchase.number.period_id, fiscal_period_name='Gestión 2026',
                number=purchase.number.number)

    def test_number_and_period_go_together(self):  # INV-01
        twin = make_purchase(self.company, date(2026, 3, 2), confirm=False)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PurchaseModel.objects.filter(pk=twin.id).update(number=5)

    def test_the_accounting_text_carries_the_period(self):  # AC-11
        confirmed = make_purchase(self.company, date(2026, 3, 1))
        self.assertEqual(_period_suffix(confirmed), ' (Gestión 2026)')
        draft = Purchase.create(supplier_id=uuid4(), purchase_date=date(2026, 3, 1))
        self.assertEqual(_period_suffix(draft), '')


class ApiTests(PurchaseApiTestCase):
    def setUp(self):
        super().setUp()
        FiscalPeriodModel.objects.filter(company_id=self.company.id).delete()
        self.period = make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))

    def confirm_url(self, purchase):
        return detail_url(purchase['id']) + 'confirm/'

    def test_a_draft_shows_the_provisional_reference_and_no_period(self):  # AC-02, AC-11
        draft = self.create()
        self.assertTrue(draft['reference'].startswith('COM-'))
        self.assertEqual((draft['number'], draft['fiscal_period']), (None, None))

    def test_confirm_assigns_the_number_and_detail_and_list_expose_it(self):  # AC-01, AC-11, API-01
        purchase = self.create()
        response = self.client.post(self.confirm_url(purchase), {}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['reference'], body['number'], body['fiscal_period']),
                         ('NC-000001', 1, {'id': str(self.period.id), 'name': 'Gestión 2026'}))
        row = self.client.get(LIST_URL).json()['results'][0]
        self.assertEqual((row['reference'], row['number'], row['fiscal_period']['name']),
                         ('NC-000001', 1, 'Gestión 2026'))

    def test_confirming_twice_returns_the_same_number(self):  # EDGE-01
        purchase = self.create()
        first = self.client.post(self.confirm_url(purchase), {}, format='json').json()
        second = self.client.post(self.confirm_url(purchase), {}, format='json').json()
        self.assertEqual((first['number'], second['number']), (1, 1))
        self.assertEqual(PurchaseNumberCounterModel.objects.get(company_id=self.company.id).last_number, 1)

    def test_confirm_without_period_is_a_409_and_the_purchase_stays_a_draft(self):  # AC-05, API-02
        purchase = self.create(purchase_date='2028-03-01')
        response = self.client.post(self.confirm_url(purchase), {}, format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'fiscal_period_missing'))
        self.assertEqual(self.client.get(detail_url(purchase['id'])).json()['status'], 'draft')

    def test_confirm_in_a_closed_period_is_a_409_with_its_name(self):  # AC-06, API-02
        FiscalPeriodModel.objects.filter(pk=self.period.id).update(status='CLOSED')
        purchase = self.create()
        response = self.client.post(self.confirm_url(purchase), {}, format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'fiscal_period_closed'))
        self.assertEqual(response.json()['period'], 'Gestión 2026')
        self.assertEqual(self.client.get(detail_url(purchase['id'])).json()['status'], 'draft')

    def test_the_list_search_finds_by_number_code_and_provisional_prefix(self):  # AC-11
        confirmed = self.create()
        self.client.post(self.confirm_url(confirmed), {}, format='json')
        draft = self.create()

        def ids(q):
            rows = self.client.get(LIST_URL, {'q': q}).json()['results']
            return {r['id'] for r in rows}

        self.assertEqual(ids('NC-000001'), {confirmed['id']})
        self.assertIn(confirmed['id'], ids('1'))
        self.assertEqual(ids('nc-1'), {confirmed['id']})
        self.assertIn(draft['id'], ids(draft['reference']))
        self.assertNotIn(draft['id'], ids('NC-000001'))

    def test_the_list_search_ignores_non_ascii_digits_instead_of_failing(self):  # AC-11 (REV-01)
        self.create()
        for text in ('²', 'nc-²', '①', '٣'):
            response = self.client.get(LIST_URL, {'q': text})
            self.assertEqual(response.status_code, 200, (text, response.content))

    def test_confirm_with_no_periods_at_all_is_a_409(self):  # EDGE-02
        FiscalPeriodModel.objects.filter(company_id=self.company.id).delete()
        purchase = self.create()
        response = self.client.post(self.confirm_url(purchase), {}, format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'fiscal_period_missing'))


class ImportedPurchaseTests(TestCase):
    """AC-10: la «compra inferida» de la importación de ventas numera igual y se rechaza sin período abierto."""

    def setUp(self):
        from decimal import Decimal

        from modules.catalog.infrastructure.django.models import ProductModel
        self.company = make_company('Empresa A')
        self.supplier = SupplierModel.objects.create(company_id=self.company.id, name='Sur')
        self.product = ProductModel.objects.create(
            company_id=self.company.id, name='Harina', sale_price=Decimal('1.00'), can_buy=True, active=True)

    def import_purchase(self, purchase_date):
        from decimal import Decimal

        from modules.purchases import services
        return services.import_received_purchase(
            self.company.id, supplier_id=self.supplier.id, purchase_date=purchase_date,
            lines=[(self.product.id, Decimal('2'), Decimal('10.00'))], warehouse_id=None, user_id=None,
            user_name='ana', post_accounting=False)

    def test_an_imported_purchase_is_numbered_in_the_period_of_its_date(self):  # AC-10
        make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        imported = self.import_purchase(date(2026, 8, 3))
        stored = PurchaseModel.objects.get(pk=imported.id)
        self.assertEqual((stored.number, stored.fiscal_period_name, stored.status), (1, 'Gestión 2026', 'confirmed'))

    def test_without_period_or_with_it_closed_the_import_is_rejected_leaving_no_purchase(self):  # AC-10, AC-05, AC-06
        from shared.import_errors import ImportRejected
        with self.assertRaises(ImportRejected) as missing, transaction.atomic():
            self.import_purchase(date(2026, 8, 3))
        self.assertEqual(missing.exception.code, 'fiscal_period_missing')
        make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31), status='CLOSED')
        with self.assertRaises(ImportRejected) as closed, transaction.atomic():
            self.import_purchase(date(2026, 8, 3))
        self.assertEqual(closed.exception.code, 'fiscal_period_closed')
        self.assertEqual(PurchaseModel.objects.filter(company_id=self.company.id).count(), 0)


class AccountingTextTests(TestCase):
    """AC-11: las descripciones de los asientos nombran el código NC y el período (el número se repite)."""

    def setUp(self):
        from types import SimpleNamespace
        from unittest import mock

        from modules.purchases.infrastructure.adapters import PurchasePostingAdapter
        self.company = make_company('Empresa A')
        self.number = PurchaseNumber(uuid4(), 'Gestión 2026', 7)
        self.purchase = SimpleNamespace(reference=self.number.code, number=self.number)
        self.receipt = SimpleNamespace(id=uuid4(), reference='REC-1', receipt_date=date(2026, 3, 1))
        self.payment = SimpleNamespace(id=uuid4(), reference='PAG-1', payment_date=date(2026, 3, 1),
                                       payment_method=SimpleNamespace(value='CASH'))
        self.actor = SimpleNamespace(user_id=None, user_name='ana')
        self.adapter = PurchasePostingAdapter(self.company.id)
        patcher = mock.patch.object(PurchasePostingAdapter, 'is_available', return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_receipt_recognition_text(self):  # AC-11
        from unittest import mock
        with mock.patch('modules.purchases.infrastructure.adapters.accounting_services.post_automatic_entry') as post:
            self.adapter.recognize_receipt(self.purchase, self.receipt, Decimal('10.00'), self.actor)
        self.assertEqual(post.call_args.args[4], 'Compra NC-000007 (Gestión 2026) - recepcion REC-1')

    def test_payment_and_advance_text(self):  # AC-11
        from unittest import mock
        with mock.patch('modules.purchases.infrastructure.adapters.accounting_services.post_automatic_entry') as post:
            self.adapter.record_payment(self.purchase, self.payment, Decimal('5.00'), Decimal('2.00'), self.actor)
        self.assertEqual([c.args[4] for c in post.call_args_list],
                         ['Pago PAG-1 de la compra NC-000007 (Gestión 2026)',
                          'Anticipo PAG-1 de la compra NC-000007 (Gestión 2026)'])

    def test_receipt_reversal_text(self):  # AC-11
        from unittest import mock
        with mock.patch('modules.purchases.infrastructure.adapters.accounting_services.reverse_automatic_entry') as rev:
            self.adapter.reverse_receipt(self.purchase, self.receipt, 'error de carga', self.actor)
        self.assertEqual(rev.call_args.args[4],
                         'Recepcion REC-1 de la compra NC-000007 (Gestión 2026) revertida: error de carga')
