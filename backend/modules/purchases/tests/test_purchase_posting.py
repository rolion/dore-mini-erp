"""COM-02: la recepción de mercadería se contabiliza (Debe Inventario / Haber Cuentas por pagar), con BD real.

Cada prueba usa Contabilidad real (cuentas por rol, período abierto, `journal_balances`).
"""
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from modules.accounting import services as accounting
from modules.accounting.application.fiscal_periods import CloseFiscalPeriod
from modules.accounting.infrastructure.django.models import (
    CoveragePeriodModel,
    JournalEntryModel,
    SettingsModel,
)
from modules.accounting.infrastructure.django.repositories import DjangoFiscalPeriodRepository
from modules.accounting.tests.journal_support import make_account, make_period
from modules.inventory.infrastructure.django.models import StockMovementModel
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled
from modules.purchases.infrastructure.django.models import PurchaseModel, ReceiptModel
from modules.purchases.tests.test_receipt_api import ReceiptApiTestCase, purchase_url

TODAY = timezone.localdate()
YESTERDAY = TODAY - timedelta(days=1)
ZERO = Decimal('0')
KIND = 'PURCHASE_RECOGNITION'
CLASSIFICATIONS = '/api/accounting/classifications/'
SETTING = '/api/purchases/payment-classification/'


class PostingTestCase(ReceiptApiTestCase):
    """Compras con Contabilidad habilitada, cuentas por rol configuradas y un período abierto que cubre hoy."""

    modules = DEFAULT_ENABLED_KEYS + ('purchases', 'inventory', 'accounting')
    configured = True

    def setUp(self):
        super().setUp()
        set_enabled(self.company, self.modules)
        self.inventory_account = make_account(self.company.id, 'Inventario', 'ASSET', '113001')
        self.payable_account = make_account(self.company.id, 'Proveedores', 'LIABILITY', '210101')
        self.period = self.make_periods()
        if self.configured:
            accounting.set_role_account(self.company.id, 'INVENTORY', self.inventory_account.id)
            accounting.set_role_account(self.company.id, 'PAYABLE', self.payable_account.id)

    def make_periods(self):
        return make_period(self.company.id, 'Año', TODAY - timedelta(days=200), TODAY + timedelta(days=100))

    def journal(self):
        return JournalEntryModel.objects.filter(company_id=self.company.id, origin_kind=KIND)

    def net(self, account):
        balance = accounting.journal_balances(self.company.id, [account.id]).get(account.id)
        return (balance.debit, balance.credit) if balance else (ZERO, ZERO)

    def lines(self, receipt_id):
        entry = self.journal().get(origin_id=receipt_id)
        return sorted((str(line.account_id), line.debit, line.credit) for line in entry.lines.all())

    def purchase_of(self, quantity, price, product=None):
        product = product or self.boxes
        return self.confirmed_purchase([(product, quantity, price)])

    def receive(self, purchase, lines, expected=201, receipt_id=None, **extra):
        extra.setdefault('warehouse_id', str(self.warehouse.id))
        return super().receive(purchase, lines, expected, receipt_id, **extra)

    def receive_date(self, purchase, lines, day, expected=201, **extra):
        body = {'receipt_id': str(uuid4()), 'receipt_date': day.isoformat(), 'warehouse_id': str(self.warehouse.id),
                'lines': [{'item_id': item, 'quantity': quantity} for item, quantity in lines], **extra}
        response = self.client.post(purchase_url(purchase['id'], 'receipts/'), body, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()


class RecognitionTests(PostingTestCase):
    def test_full_reception_debits_inventory_and_credits_payable(self):  # AC-01
        purchase = self.purchase_of('100', '10.00')  # 1.000
        item = self.item_id(purchase, self.boxes)
        receipt = self.receive(purchase, [(item, '100')])
        self.assertEqual(self.journal().count(), 1)
        self.assertEqual(self.lines(receipt['id']), sorted([
            (str(self.inventory_account.id), Decimal('1000.00'), ZERO),
            (str(self.payable_account.id), ZERO, Decimal('1000.00'))]))
        self.assertEqual(self.net(self.inventory_account), (Decimal('1000.00'), ZERO))
        self.assertEqual(self.net(self.payable_account), (ZERO, Decimal('1000.00')))

    def test_partial_receptions_recognize_each_amount_and_add_up_to_the_total(self):  # AC-02
        purchase = self.confirmed_purchase()  # harina 10 x 5.00 + bolsa 4 x 2.00 = 58.00
        flour, bag = self.item_id(purchase, self.flour), self.item_id(purchase, self.bag)
        first = self.receive(purchase, [(flour, '4')])
        self.assertEqual(self.net(self.payable_account), (ZERO, Decimal('20.00')))
        second = self.receive(purchase, [(flour, '6'), (bag, '4')])
        self.assertEqual(self.journal().count(), 2)
        debits = [line[1] for line in self.lines(first['id']) + self.lines(second['id']) if line[1]]
        self.assertEqual(sorted(debits), [Decimal('20.00'), Decimal('38.00')])
        self.assertEqual(self.net(self.payable_account), (ZERO, Decimal('58.00')))
        self.assertEqual(self.net(self.inventory_account), (Decimal('58.00'), ZERO))

    def test_rounding_never_drifts_across_partial_receptions(self):  # INV-01
        purchase = self.purchase_of('0.3', '0.15', product=self.flour)  # total 0.05 (0.045 redondeado)
        item = self.item_id(purchase, self.flour)
        for _ in range(3):
            self.receive(purchase, [(item, '0.1')])
        self.assertEqual(self.purchase_detail(purchase)['total'], '0.05')
        self.assertEqual(self.net(self.payable_account), (ZERO, Decimal('0.05')))

    def test_zero_priced_reception_posts_nothing(self):  # INV-04
        purchase = self.purchase_of('5', '0.00')
        self.receive(purchase, [(self.item_id(purchase, self.boxes), '5')])
        self.assertEqual(self.journal().count(), 0)


class IdempotencyAndAtomicityTests(PostingTestCase):
    def test_retrying_the_same_reception_does_not_duplicate_the_entry(self):  # AC-04
        purchase = self.purchase_of('100', '10.00')
        item = self.item_id(purchase, self.boxes)
        receipt_id = uuid4()
        self.receive(purchase, [(item, '100')], receipt_id=receipt_id)
        self.receive(purchase, [(item, '100')], expected=200, receipt_id=receipt_id)
        self.assertEqual(self.journal().count(), 1)
        self.assertEqual(self.net(self.payable_account), (ZERO, Decimal('1000.00')))

    def test_recognizing_the_same_receipt_from_another_module_returns_the_existing_entry(self):  # AC-04
        purchase = self.purchase_of('100', '10.00')
        receipt = self.receive(purchase, [(self.item_id(purchase, self.boxes), '100')])
        with transaction.atomic():
            again = accounting.post_automatic_entry(self.company.id, KIND, ReceiptModel.objects.get(
                pk=receipt['id']).pk, TODAY, 'Otra', Decimal('1000.00'))
        self.assertFalse(again.created)
        self.assertEqual(self.journal().count(), 1)

    def test_draft_confirm_and_cancel_do_not_move_accounts(self):  # AC-05
        created = self.client.post('/api/purchases/', {
            'supplier_id': str(self.supplier.id), 'purchase_date': '2026-10-20',
            'items': [{'product_id': str(self.boxes.id), 'quantity': '10', 'unit_price': '10.00'}]},
            format='json').json()
        self.client.post(purchase_url(created['id'], 'confirm/'), format='json')
        self.client.post(purchase_url(created['id'], 'cancel/'), {'reason': 'No va'}, format='json')
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 0)
        self.assertEqual(self.net(self.payable_account), (ZERO, ZERO))


class CoverageAndRejectionTests(PostingTestCase):
    def test_reception_before_the_cutoff_posts_nothing_and_succeeds(self):  # AC-06
        purchase = self.purchase_of('10', '10.00')
        accounting.coverage_status(self.company.id, TODAY)  # fija el corte en hoy
        self.receive_date(purchase, [(self.item_id(purchase, self.boxes), '10')], YESTERDAY)
        self.assertEqual(self.journal().count(), 0)
        self.assertEqual(ReceiptModel.objects.count(), 1)

    def test_closed_period_rejects_without_saving_anything(self):  # AC-05, AC-06
        purchase = self.purchase_of('10', '10.00')
        with transaction.atomic():
            CloseFiscalPeriod(DjangoFiscalPeriodRepository(self.company.id)).execute(
                self.period.id, 'ana', timezone.now())
        response = self.client.post(purchase_url(purchase['id'], 'receipts/'), {
            'receipt_id': str(uuid4()), 'receipt_date': TODAY.isoformat(), 'warehouse_id': str(self.warehouse.id),
            'lines': [{'item_id': self.item_id(purchase, self.boxes), 'quantity': '10'}]}, format='json')
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()['code'], 'fiscal_period_unavailable')
        self.assertEqual((ReceiptModel.objects.count(), self.journal().count()), (0, 0))
        self.assertEqual(self.purchase_detail(purchase)['reception_status'], 'not_received')


class GapCoverageTests(PostingTestCase):
    def test_a_reception_inside_a_coverage_gap_posts_nothing_and_succeeds(self):  # AC-06
        now = timezone.now()
        SettingsModel.objects.create(company_id=self.company.id, cutoff_date=TODAY - timedelta(days=60))
        CoveragePeriodModel.objects.create(company_id=self.company.id, started_at=now - timedelta(days=30),
                                           ended_at=now - timedelta(days=10))
        CoveragePeriodModel.objects.create(company_id=self.company.id, started_at=now - timedelta(days=6))
        during = (now - timedelta(days=8)).astimezone().date()
        self.assertEqual(accounting.coverage_status(self.company.id, during).reason, 'in_gap')
        purchase = self.purchase_of('10', '10.00')
        self.receive_date(purchase, [(self.item_id(purchase, self.boxes), '10')], during)
        self.assertEqual((self.journal().count(), ReceiptModel.objects.count()), (0, 1))


class MissingConfigurationTests(PostingTestCase):
    configured = False

    def test_missing_accounts_reject_with_actionable_issues_and_save_nothing(self):  # AC-05, AC-06
        purchase = self.purchase_of('10', '10.00')
        response = self.client.post(purchase_url(purchase['id'], 'receipts/'), {
            'receipt_id': str(uuid4()), 'receipt_date': TODAY.isoformat(), 'warehouse_id': str(self.warehouse.id),
            'lines': [{'item_id': self.item_id(purchase, self.boxes), 'quantity': '10'}]}, format='json')
        self.assertEqual(response.status_code, 409, response.content)
        body = response.json()
        self.assertEqual(body['code'], 'posting_configuration_missing')
        self.assertEqual({i['role'] for i in body['issues']}, {'INVENTORY', 'PAYABLE'})
        self.assertEqual((ReceiptModel.objects.count(), self.journal().count()), (0, 0))
        self.assertEqual(PurchaseModel.objects.get(pk=purchase['id']).reception_status, 'not_received')


class ReversalTests(PostingTestCase):
    def revert(self, purchase, receipt, expected=200):
        response = self.client.post(purchase_url(purchase['id'], f'receipts/{receipt["id"]}/revert/'),
                                    {'reason': 'Error de conteo'}, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def test_reverting_the_reception_reverses_its_entry(self):  # AC-07
        purchase = self.purchase_of('100', '10.00')
        receipt = self.receive(purchase, [(self.item_id(purchase, self.boxes), '100')])
        self.revert(purchase, receipt)
        self.assertEqual(self.net(self.payable_account), (Decimal('1000.00'), Decimal('1000.00')))
        self.assertEqual(self.net(self.inventory_account), (Decimal('1000.00'), Decimal('1000.00')))
        self.assertEqual(self.purchase_detail(purchase)['reception_status'], 'not_received')

    def test_reverting_a_reception_without_entry_still_works(self):  # AC-07
        purchase = self.purchase_of('10', '10.00')
        self.accounting_off()
        receipt = self.receive(purchase, [(self.item_id(purchase, self.boxes), '10')])
        self.accounting_on()
        self.assertEqual(self.journal().count(), 0)
        self.revert(purchase, receipt)
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 0)

    def test_closed_period_blocks_the_reversal_entirely(self):  # AC-07
        purchase = self.purchase_of('10', '10.00')
        receipt = self.receive(purchase, [(self.item_id(purchase, self.boxes), '10')])
        with transaction.atomic():
            CloseFiscalPeriod(DjangoFiscalPeriodRepository(self.company.id)).execute(
                self.period.id, 'ana', timezone.now())
        body = self.revert(purchase, receipt, expected=409)
        self.assertEqual(body['code'], 'fiscal_period_unavailable')
        self.assertEqual(ReceiptModel.objects.get(pk=receipt['id']).status, 'confirmed')
        self.assertEqual(self.purchase_detail(purchase)['reception_status'], 'received')

    def test_reverting_after_disabling_accounting_still_reverses_the_existing_entry(self):  # REV-02
        purchase = self.purchase_of('100', '10.00')
        receipt = self.receive(purchase, [(self.item_id(purchase, self.boxes), '100')])
        self.accounting_off()
        self.revert(purchase, receipt)
        self.accounting_on()
        self.assertEqual(self.net(self.payable_account), (Decimal('1000.00'), Decimal('1000.00')))

    def test_net_payable_equals_the_total_after_reverting_an_intermediate_reception(self):  # REV-01
        purchase = self.purchase_of('0.3', '0.15', product=self.flour)
        item = self.item_id(purchase, self.flour)
        first = self.receive(purchase, [(item, '0.1')])
        self.receive(purchase, [(item, '0.1')])
        self.revert(purchase, first)
        self.receive(purchase, [(item, '0.2')])
        debit, credit = self.net(self.payable_account)
        self.assertEqual(credit - debit, Decimal('0.05'))

    def accounting_off(self):
        set_enabled(self.company, DEFAULT_ENABLED_KEYS + ('purchases', 'inventory'))

    def accounting_on(self):
        set_enabled(self.company, self.modules)


class LinkAndIndependenceTests(PostingTestCase):
    def test_receipt_detail_links_the_entry(self):  # AC-08
        purchase = self.purchase_of('10', '10.00')
        receipt = self.receive(purchase, [(self.item_id(purchase, self.boxes), '10')])
        entry = self.journal().get(origin_id=receipt['id'])
        self.assertEqual(receipt['accounting_entry']['id'], str(entry.id))
        self.assertEqual((receipt['accounting_entry']['total'], receipt['accounting_enabled']), ('100.00', True))
        self.assertIn(purchase['reference'], entry.description)
        self.assertIn(receipt['reference'], entry.description)
        detail = self.client.get(purchase_url(purchase['id'], f'receipts/{receipt["id"]}/')).json()
        self.assertEqual(detail['accounting_entry']['id'], str(entry.id))

    def test_documental_reception_without_inventory_still_posts(self):  # AC-09
        set_enabled(self.company, DEFAULT_ENABLED_KEYS + ('purchases', 'accounting'))
        purchase = self.purchase_of('10', '10.00', product=self.flour)
        receipt = self.receive(purchase, [(self.item_id(purchase, self.flour), '10')])
        self.assertEqual(receipt['inventory_mode'], 'documental')
        self.assertEqual(self.net(self.payable_account), (ZERO, Decimal('100.00')))
        self.assertEqual(StockMovementModel.objects.count(), 0)

    def test_without_accounting_nothing_changes(self):  # AC-09
        set_enabled(self.company, DEFAULT_ENABLED_KEYS + ('purchases', 'inventory'))
        purchase = self.purchase_of('10', '10.00')
        receipt = self.receive(purchase, [(self.item_id(purchase, self.boxes), '10')])
        self.assertEqual((receipt['accounting_entry'], receipt['accounting_enabled']), (None, False))
        self.assertEqual(JournalEntryModel.objects.count(), 0)
