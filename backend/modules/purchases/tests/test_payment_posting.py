"""COM-01 (en COM-02 v2): el pago se contabiliza contra Cuentas por pagar o como anticipo a proveedores."""
import threading
import time
from datetime import timedelta
from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.db import close_old_connections, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from .numbering_support import fake_number
from modules.accounting import services as accounting
from modules.accounting.application.fiscal_periods import CloseFiscalPeriod
from modules.accounting.infrastructure.django.models import JournalEntryModel
from modules.accounting.infrastructure.django.repositories import DjangoFiscalPeriodRepository
from modules.accounts.testing import make_company
from modules.expenses.infrastructure.django.models import ExpenseModel
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled
from modules.purchases.application.payment_commands import RegisterPayment
from modules.purchases.application.ports import Actor
from modules.purchases.domain.exceptions import PurchaseValidationError
from modules.purchases.domain.purchase import ItemDraft, Purchase
from modules.purchases.infrastructure.adapters import PurchasePostingAdapter
from modules.purchases.infrastructure.django.models import PaymentModel, SupplierModel
from modules.purchases.infrastructure.django.payment_repository import DjangoPaymentRepository
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository
from modules.purchases.infrastructure.django.receipt_repository import DjangoReceiptRepository
from modules.purchases.tests.payment_support import PaymentBooks
from modules.purchases.tests.test_payment_api import PaymentApiTestCase, purchase_url

TODAY = timezone.localdate()
YESTERDAY = TODAY - timedelta(days=1)
ZERO = Decimal('0')
D = Decimal
PAYMENT, ADVANCE, RECOGNITION = 'PURCHASE_PAYMENT', 'PURCHASE_ADVANCE', 'PURCHASE_RECOGNITION'


class PaymentPostingCase(PaymentApiTestCase):
    """Compra de harina de 100 kg a 10.00 (total 1.000,00) con Contabilidad configurada."""
    advances = True

    def setUp(self):
        super().setUp()
        self.books = PaymentBooks(self.company, advances=self.advances)

    def purchase(self):
        return self.confirmed_purchase('100', '10.00')

    def receive(self, purchase, quantity, expected=201):
        body = {'receipt_id': str(uuid4()), 'receipt_date': TODAY.isoformat(),
                'lines': [{'item_id': purchase['items'][0]['id'], 'quantity': quantity}]}
        response = self.client.post(purchase_url(purchase['id'], 'receipts/'), body, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def pay_with(self, purchase, amount, method='CASH', expected=201, payment_id=None, day=None):
        body = {'payment_id': str(payment_id or uuid4()), 'amount': amount, 'payment_method': method,
                'payment_date': (day or TODAY).isoformat()}
        response = self.client.post(purchase_url(purchase['id'], 'payments/'), body, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def entries(self, payment):
        return {kind: self.books.journal(kind).filter(origin_id=payment['id']).first()
                for kind in (PAYMENT, ADVANCE)}


class PayRecognizedDebtTests(PaymentPostingCase):
    def test_two_payments_with_different_methods_settle_the_debt(self):  # AC-11
        purchase = self.purchase()
        self.receive(purchase, '100')
        cash = self.pay_with(purchase, '300.00', 'CASH')
        bank = self.pay_with(purchase, '700.00', 'BANK_TRANSFER')
        b = self.books
        self.assertEqual(b.lines(PAYMENT, cash['id']), sorted([
            (b.payable.id, D('300.00'), ZERO), (b.caja.id, ZERO, D('300.00'))]))
        self.assertEqual(b.lines(PAYMENT, bank['id']), sorted([
            (b.payable.id, D('700.00'), ZERO), (b.banco.id, ZERO, D('700.00'))]))
        self.assertEqual(b.net(b.payable), (D('1000.00'), D('1000.00')))  # deuda cero
        self.assertEqual(b.journal(ADVANCE).count(), 0)
        self.assertEqual((cash['debt_amount'], cash['advance_amount']), ('300.00', '0.00'))
        self.assertEqual(self.detail(purchase)['payment_status'], 'paid')

    def test_paying_changes_neither_inventory_nor_expenses_and_a_retry_adds_nothing(self):  # AC-12
        purchase = self.purchase()
        self.receive(purchase, '100')
        inventory_before = self.books.net(self.books.inventory)
        payment_id = uuid4()
        self.pay_with(purchase, '300.00', payment_id=payment_id)
        self.pay_with(purchase, '300.00', expected=200, payment_id=payment_id)
        self.assertEqual(self.books.net(self.books.inventory), inventory_before)
        self.assertEqual(ExpenseModel.objects.count(), 0)
        self.assertEqual((self.books.journal(PAYMENT).count(), PaymentModel.objects.count()), (1, 1))
        self.assertEqual(self.books.journal(RECOGNITION).count(), 1)

    def test_the_payment_list_links_each_entry_and_the_preview_writes_nothing(self):  # AC-18, AC-19
        purchase = self.purchase()
        self.receive(purchase, '40')  # deuda reconocida 400
        paid = self.pay_with(purchase, '500.00')  # 400 deuda + 100 anticipo
        listed = self.client.get(purchase_url(purchase['id'], 'payments/')).json()['results'][0]
        self.assertEqual(sorted(e['kind'] for e in listed['accounting_entries']), ['advance', 'debt'])
        self.assertEqual(sorted(e['total'] for e in paid['accounting_entries']), ['100.00', '400.00'])
        before = JournalEntryModel.objects.count()
        preview = self.client.get(purchase_url(purchase['id'], 'payments/preview/'),
                                  {'amount': '500.00', 'payment_method': 'CASH', 'payment_date': TODAY.isoformat()})
        self.assertEqual(preview.status_code, 200, preview.content)
        self.assertEqual(JournalEntryModel.objects.count(), before)


class AdvanceTests(PaymentPostingCase):
    def test_paying_before_receiving_is_a_supplier_advance(self):  # AC-15
        purchase = self.purchase()
        paid = self.pay_with(purchase, '400.00')
        b = self.books
        self.assertEqual(b.lines(ADVANCE, paid['id']), sorted([
            (b.advances.id, D('400.00'), ZERO), (b.caja.id, ZERO, D('400.00'))]))
        self.assertEqual(b.journal(PAYMENT).count(), 0)
        self.assertEqual(b.net(b.payable), (ZERO, ZERO))  # no se inventa deuda
        self.assertEqual(ExpenseModel.objects.count(), 0)
        self.assertEqual((paid['debt_amount'], paid['advance_amount']), ('0.00', '400.00'))

    def test_a_mixed_payment_creates_both_entries(self):  # AC-15
        purchase = self.purchase()
        self.receive(purchase, '40')
        paid = self.pay_with(purchase, '500.00')
        entries = self.entries(paid)
        debits = {kind: sum(line.debit for line in entry.lines.all()) for kind, entry in entries.items()}
        self.assertEqual(debits, {PAYMENT: D('400.00'), ADVANCE: D('100.00')})
        self.assertEqual((paid['debt_amount'], paid['advance_amount']), ('400.00', '100.00'))

    def test_the_advance_is_applied_when_the_goods_arrive(self):  # AC-16
        purchase = self.purchase()
        self.pay_with(purchase, '1000.00')
        b = self.books
        first = self.receive(purchase, '40')
        self.assertEqual(b.lines(RECOGNITION, first['id']), sorted([
            (b.inventory.id, D('400.00'), ZERO), (b.advances.id, ZERO, D('400.00'))]))
        self.receive(purchase, '60')
        self.assertEqual(b.net(b.advances), (D('1000.00'), D('1000.00')))
        self.assertEqual(b.net(b.payable), (ZERO, ZERO))
        self.assertEqual(b.net(b.inventory), (D('1000.00'), ZERO))

    def test_a_partial_advance_leaves_the_rest_as_payable(self):  # AC-16
        purchase = self.purchase()
        self.receive(purchase, '40')
        self.pay_with(purchase, '500.00')  # 400 deuda + 100 anticipo
        b = self.books
        second = self.receive(purchase, '60')  # 600: aplica 100 de anticipo
        self.assertEqual(b.lines(RECOGNITION, second['id']), sorted([
            (b.inventory.id, D('600.00'), ZERO), (b.payable.id, ZERO, D('500.00')),
            (b.advances.id, ZERO, D('100.00'))]))
        last = self.pay_with(purchase, '500.00')
        self.assertEqual((last['debt_amount'], last['advance_amount']), ('500.00', '0.00'))
        debit, credit = b.net(b.payable)
        self.assertEqual(debit, credit)  # deuda cero
        self.assertEqual(b.net(b.advances), (D('100.00'), D('100.00')))

    def test_reverting_the_reception_makes_the_advance_pending_again(self):  # AC-16
        purchase = self.purchase()
        self.pay_with(purchase, '1000.00')
        self.receive(purchase, '40')
        second = self.receive(purchase, '60')
        response = self.client.post(purchase_url(purchase['id'], f'receipts/{second["id"]}/revert/'),
                                    {'reason': 'Error'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        debit, credit = self.books.net(self.books.advances)
        self.assertEqual(debit - credit, D('600.00'))  # pendiente otra vez: 1.000 pagados − 400 aplicados
        again = self.receive(purchase, '60')
        self.assertEqual(self.books.lines(RECOGNITION, again['id']), sorted([
            (self.books.inventory.id, D('600.00'), ZERO), (self.books.advances.id, ZERO, D('600.00'))]))


class RejectionTests(PaymentPostingCase):
    def test_an_advance_without_the_advances_account_is_rejected_but_paying_debt_is_not(self):  # AC-14, AC-17
        accounting.set_role_account(self.company.id, 'SUPPLIER_ADVANCES', None)
        purchase = self.purchase()
        body = self.pay_with(purchase, '400.00', expected=409)
        self.assertEqual(body['code'], 'posting_configuration_missing')
        self.assertEqual({i['role'] for i in body['issues']}, {'SUPPLIER_ADVANCES'})
        self.assertEqual((PaymentModel.objects.count(), self.books.journal().count()), (0, 0))
        self.receive(purchase, '100')
        self.pay_with(purchase, '300.00')

    def test_a_method_without_an_active_account_is_rejected_and_nothing_is_saved(self):  # AC-14
        purchase = self.purchase()
        self.receive(purchase, '100')
        self.books.map_method('CASH', self.books.caja, active=False)
        body = self.pay_with(purchase, '300.00', expected=409)
        self.assertEqual(body['code'], 'posting_configuration_missing')
        self.assertEqual((PaymentModel.objects.filter(purchase_id=purchase['id']).count(),
                          self.books.journal(PAYMENT).count()), (0, 0))
        self.assertEqual(self.detail(purchase)['payment_status'], 'unpaid')

    def test_a_closed_period_rejects_the_payment_entirely(self):  # AC-14
        purchase = self.purchase()
        self.receive(purchase, '100')
        with transaction.atomic():
            CloseFiscalPeriod(DjangoFiscalPeriodRepository(self.company.id)).execute(
                self.books.period.id, 'ana', timezone.now())
        body = self.pay_with(purchase, '300.00', expected=409)
        self.assertEqual(body['code'], 'fiscal_period_unavailable')
        self.assertEqual(PaymentModel.objects.count(), 0)

    def test_a_ledger_failure_after_saving_rolls_the_payment_back(self):  # AC-14
        purchase = self.purchase()
        self.receive(purchase, '100')
        with mock.patch.object(accounting, 'post_automatic_entry',
                               side_effect=accounting.JournalValidationError({'amount': ['No válido.']})):
            body = self.pay_with(purchase, '300.00', expected=409)
        self.assertEqual(body['code'], 'ledger_rejected')
        self.assertEqual((PaymentModel.objects.count(), self.detail(purchase)['paid_total']), (0, '0.00'))


class NoCoverageAndClassificationTests(PaymentPostingCase):
    def test_classification_is_no_longer_required(self):  # AC-20
        purchase = self.purchase()
        self.receive(purchase, '100')
        paid = self.pay_with(purchase, '300.00')
        self.assertIsNone(paid['classification'])

    def test_a_payment_before_the_cutoff_is_saved_without_entry_and_counts_as_debt_paid(self):  # AC-21
        purchase = self.purchase()
        accounting.coverage_status(self.company.id, TODAY)  # fija el corte en hoy
        paid = self.pay_with(purchase, '400.00', day=YESTERDAY)
        self.assertEqual((paid['debt_amount'], paid['advance_amount'], paid['accounting_entries']),
                         ('400.00', '0.00', []))
        self.assertEqual(self.books.journal().count(), 0)

    def test_without_accounting_nothing_changes(self):  # AC-21
        set_enabled(self.company, (*DEFAULT_ENABLED_KEYS, 'purchases'))
        purchase = self.purchase()
        paid = self.pay_with(purchase, '400.00')
        self.assertEqual((paid['debt_amount'], paid['accounting_entries']), ('400.00', []))
        self.assertEqual(self.books.journal().count(), 0)


class PreviewTests(PaymentPostingCase):
    def preview(self, purchase, **query):
        query = {'amount': '300.00', 'payment_method': 'CASH', 'payment_date': TODAY.isoformat(), **query}
        return self.client.get(purchase_url(purchase['id'], 'payments/preview/'), query)

    def test_preview_shows_the_split_the_lines_and_the_account_names(self):  # AC-18
        purchase = self.purchase()
        self.receive(purchase, '40')
        body = self.preview(purchase, amount='500.00').json()
        self.assertEqual((body['covered'], body['debt_amount'], body['advance_amount']), (True, '400.00', '100.00'))
        self.assertEqual([(l['side'], l['role'], l['account']['name'], l['amount']) for l in body['lines']], [
            ('DEBIT', 'PAYABLE', 'Proveedores', '400.00'), ('CREDIT', 'MONEY', 'Caja', '400.00'),
            ('DEBIT', 'SUPPLIER_ADVANCES', 'Anticipos a proveedores', '100.00'), ('CREDIT', 'MONEY', 'Caja', '100.00')])
        self.assertEqual(body['issues'], [])

    def test_preview_reports_missing_configuration_and_invalid_input(self):  # AC-18
        accounting.set_role_account(self.company.id, 'PAYABLE', None)
        purchase = self.purchase()
        self.receive(purchase, '100', expected=409)
        self.assertEqual(self.preview(purchase, amount='0').status_code, 400)
        self.assertEqual(self.preview(purchase, payment_method='XX').status_code, 400)

    def test_preview_without_coverage_says_no_entry(self):  # AC-18
        set_enabled(self.company, (*DEFAULT_ENABLED_KEYS, 'purchases'))
        body = self.preview(self.purchase()).json()
        self.assertEqual((body['covered'], body['lines']), (False, []))


class ConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('Empresa C')
        self.books = PaymentBooks(self.company)
        supplier = SupplierModel.objects.create(company_id=self.company.id, name='Sur')
        purchase = Purchase.create(supplier_id=supplier.id, purchase_date=TODAY,
                                   items=[ItemDraft(uuid4(), '100', '10.00', product_name='Harina')])
        purchase.confirm(timezone.now(), fake_number())
        self.purchase = DjangoPurchaseRepository(self.company.id).save(purchase)

    def register(self, amount):
        def action():
            use_case = RegisterPayment(
                DjangoPurchaseRepository(self.company.id), DjangoPaymentRepository(self.company.id),
                posting=PurchasePostingAdapter(self.company.id), receipts=DjangoReceiptRepository(self.company.id))
            return use_case.execute(self.purchase.id, uuid4(), amount, 'CASH', TODAY, Actor(None, 'Ana'), TODAY)
        return action

    def test_two_simultaneous_payments_cannot_both_exceed_the_balance(self):  # AC-13
        holding = threading.Event()
        results = {}
        original = DjangoPurchaseRepository.save

        def slow_save(repo, purchase):
            holding.set()
            time.sleep(0.6)  # conserva el bloqueo de la compra mientras el otro hilo intenta entrar
            return original(repo, purchase)

        def run(name, action):
            try:
                with transaction.atomic():
                    results[name] = action()
            except Exception as exc:  # noqa: BLE001 - se informa al test
                results[name] = exc
            finally:
                close_old_connections()

        with mock.patch.object(DjangoPurchaseRepository, 'save', slow_save):
            a = threading.Thread(target=run, args=('first', self.register('700.00')))
            b = threading.Thread(target=run, args=('second', self.register('700.00')))
            a.start()
            self.assertTrue(holding.wait(5))
            b.start()
            a.join(15)
            b.join(15)
        failures = [r for r in results.values() if isinstance(r, Exception)]
        self.assertEqual(len(failures), 1, results)
        self.assertIsInstance(failures[0], PurchaseValidationError)
        self.assertEqual(PaymentModel.objects.filter(purchase_id=self.purchase.id).count(), 1)
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 1)
