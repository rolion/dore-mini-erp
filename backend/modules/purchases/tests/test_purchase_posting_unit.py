"""COM-02: reconocimiento de la recepción sin base de datos (dominio, comandos con puerto falso, errores)."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from django.test import SimpleTestCase

from modules.accounting import services as accounting_services
from modules.purchases.api.receipt_serializers import receipt_representation
from modules.purchases.application.ports import PostedEntry
from modules.purchases.application.purchase_commands import ConfirmPurchase, ItemInput
from modules.purchases.application.receipt_commands import (
    ReceiptLineInput,
    RegisterReception,
    RevertReception,
    RevertStockShortage,
)
from modules.purchases.application.receipt_queries import ReceiptDetail
from modules.purchases.domain.enums import ReceiptStatus
from modules.purchases.domain.exceptions import PostingRejected, StockShortage
from modules.purchases.domain.enums import PaymentMethod
from modules.purchases.domain.payment import Payment
from modules.purchases.domain.purchase import ItemDraft, Purchase, split_payment
from modules.purchases.domain.receipt import Receipt
from modules.purchases.infrastructure.adapters import _posting_errors
from modules.purchases.tests.test_receipt_application import ACTOR, NOW, TODAY, ReceptionCase

D = Decimal


def purchase_of(quantity, price):
    purchase = Purchase.create(supplier_id=uuid4(), purchase_date=TODAY,
                               items=[ItemDraft(uuid4(), quantity, price, product_name='Harina')])
    purchase.confirm(NOW)
    return purchase


def receipt_of(purchase, quantity):
    from modules.purchases.domain.purchase import ReceiptLineDraft
    return purchase.receive(uuid4(), TODAY, TODAY, {}, [ReceiptLineDraft(purchase.items[0].id, quantity, True)],
                            None, 'Ana')


class ReceiptAmountTests(SimpleTestCase):
    def test_full_and_partial_amounts_use_the_line_price(self):  # INV-01
        purchase = purchase_of('10', '5.00')
        self.assertEqual(purchase.receipt_amount(receipt_of(purchase, '10'), {}, D('0')), D('50.00'))
        self.assertEqual(purchase.receipt_amount(receipt_of(purchase, '4'), {}, D('0')), D('20.00'))

    def test_a_later_reception_is_valued_as_the_difference_of_the_cumulative_value(self):  # INV-01
        purchase = purchase_of('10', '5.00')
        item = purchase.items[0].id
        self.assertEqual(purchase.receipt_amount(receipt_of(purchase, '6'), {item: D('4')}, D('20.00')), D('30.00'))

    def test_zero_price_gives_zero(self):  # INV-04
        purchase = purchase_of('10', '0.00')
        self.assertEqual(purchase.receipt_amount(receipt_of(purchase, '10'), {}, D('0')), D('0.00'))

    def test_rounding_never_drifts_after_reverting_an_intermediate_reception(self):  # INV-01, REV-01
        purchase = purchase_of('0.3', '0.15')  # subtotal 0.05
        item = purchase.items[0].id
        # A=0.1 (0.02) y B=0.1 (0.01); se revierte A: quedan B=0.1 reconocido 0.01. Recibir C=0.2 reconoce lo que falta.
        amount = purchase.receipt_amount(receipt_of(purchase, '0.2'), {item: D('0.1')}, D('0.01'))
        self.assertEqual(amount, D('0.04'))
        self.assertEqual(D('0.01') + amount, D('0.05'))


class FakePosting:
    def __init__(self, enabled=True, reject=None):
        self.enabled, self.reject = enabled, reject
        self.recognized: dict = {}
        self.calls: list = []

    def is_available(self):
        return self.enabled

    def covers(self, on):
        return self.enabled

    def recognize_receipt(self, purchase, receipt, amount, actor, advance_applied=D('0')):
        if self.reject:
            raise self.reject
        self.calls.append(('recognize', receipt.id, amount))
        self.recognized[receipt.id] = amount

    def reverse_receipt(self, purchase, receipt, reason, actor):
        self.calls.append(('reverse', receipt.id))

    def recognized_totals(self, receipt_ids):
        self.calls.append(('totals',))
        return {rid: self.recognized[rid] for rid in receipt_ids if rid in self.recognized}

    def entry_for(self, receipt_id):
        return None


class PostingReceptionCase(ReceptionCase):
    def setUp(self):
        super().setUp()
        self.posting = FakePosting()

    def register_posting(self, quantity='4', receipt_id=None, item_id=None, purchase_id=None, warehouse_id=None):
        use_case = RegisterReception(self.purchases, self.receipts, self.products, self.stock, self.posting)
        return use_case.execute(purchase_id or self.purchase.id, receipt_id or uuid4(), TODAY,
                                [ReceiptLineInput(item_id or self.item_id, quantity)], warehouse_id, ACTOR, TODAY)

    def recognitions(self):
        return [call for call in self.posting.calls if call[0] == 'recognize']


class RegisterReceptionPostingTests(PostingReceptionCase):
    def test_publishes_the_received_amount_once(self):  # AC-01, AC-04
        receipt, created = self.register_posting('4')
        self.assertTrue(created)
        self.assertEqual(self.recognitions(), [('recognize', receipt.id, D('20.00'))])

    def test_a_retry_with_the_same_receipt_id_does_not_publish_again(self):  # AC-04
        receipt_id = uuid4()
        self.register_posting('4', receipt_id)
        _, created = self.register_posting('4', receipt_id)
        self.assertFalse(created)
        self.assertEqual(len(self.recognitions()), 1)

    def test_a_rejection_propagates(self):  # AC-05
        self.posting.reject = PostingRejected('fiscal_period_unavailable', 'Período cerrado.')
        with self.assertRaises(PostingRejected):
            self.register_posting('4')

    def test_disabled_accounting_does_nothing_and_does_not_query(self):  # AC-09
        self.posting.enabled = False
        self.register_posting('4')
        self.assertEqual(self.posting.calls, [])

    def test_zero_priced_line_publishes_nothing(self):  # INV-04
        purchase = self.create(items=[ItemInput(self.flour.id, '10', '0.00')])
        ConfirmPurchase(self.purchases, self.suppliers).execute(purchase.id, NOW)
        self.register_posting('10', item_id=purchase.items[0].id, purchase_id=purchase.id)
        self.assertEqual(self.recognitions(), [])

    def test_net_recognized_equals_the_total_after_reverting_an_intermediate_reception(self):  # INV-01, REV-01
        purchase = self.create(items=[ItemInput(self.flour.id, '0.3', '0.15')])
        ConfirmPurchase(self.purchases, self.suppliers).execute(purchase.id, NOW)
        item = purchase.items[0].id
        first, _ = self.register_posting('0.1', item_id=item, purchase_id=purchase.id)
        second, _ = self.register_posting('0.1', item_id=item, purchase_id=purchase.id)
        first.status = ReceiptStatus.REVERTED
        self.receipts.received_totals = lambda pid: {  # la recepción falsa cuenta también las revertidas
            item: sum((l.quantity for r in (second,) for l in r.lines), D('0'))}
        third, _ = self.register_posting('0.2', item_id=item, purchase_id=purchase.id)
        active = [r for r in (second, third)]
        self.assertEqual(sum(self.posting.recognized[r.id] for r in active), D('0.05'))


class RecordingReceipts:
    """Recepciones falsas que anotan, en la lista de llamadas del puerto, cuándo se marca una como revertida."""

    def __init__(self, receipts, calls):
        self.receipts, self.calls = receipts, calls

    def get(self, receipt_id):
        return self.receipts.get(receipt_id)

    def mark_reverted(self, receipt):
        self.calls.append(('mark_reverted', receipt.id))

    def received_totals(self, purchase_id):
        return {}


class FailingStock:
    def __init__(self, fail):
        self.fail = fail

    def is_available(self):
        return True

    def reverse_entries(self, receipt_id, reason, actor):
        if self.fail:
            raise StockShortage(uuid4(), [(uuid4(), D('4'), D('1'))])

    def movements_for(self, receipt_id):
        return []


class RevertReceptionPostingTests(PostingReceptionCase):
    def revert(self, receipt, stock):
        use_case = RevertReception(self.purchases, RecordingReceipts(self.receipts, self.posting.calls), stock,
                                   self.posting)
        return use_case.execute(self.purchase.id, receipt.id, 'Error de conteo', ACTOR, NOW)

    def moved_receipt(self):
        self.with_inventory()
        receipt, _ = self.register_posting('4', warehouse_id=self.warehouse.id)
        return receipt

    def test_the_entry_is_reversed_before_the_receipt_is_marked_reverted(self):  # AC-07
        receipt = self.moved_receipt()
        self.posting.calls.clear()
        self.revert(receipt, FailingStock(False))
        self.assertEqual(self.posting.calls, [('reverse', receipt.id), ('mark_reverted', receipt.id)])

    def test_a_stock_shortage_does_not_reverse_the_entry(self):  # AC-07, edge
        receipt = self.moved_receipt()
        self.posting.calls.clear()
        with self.assertRaises(RevertStockShortage):
            self.revert(receipt, FailingStock(True))
        self.assertEqual(self.posting.calls, [])


class AdapterErrorMappingTests(SimpleTestCase):
    def test_engine_rejections_become_actionable_posting_errors(self):  # AC-06
        cases = [
            (accounting_services.JournalValidationError({'amount': ['Monto no válido.']}), 'ledger_rejected'),
            (accounting_services.JournalConflict('origin_conflict', 'Otro asiento.', ['amount']), 'ledger_conflict'),
            (accounting_services.FiscalPeriodClosed('Año', date(2026, 10, 30)), 'fiscal_period_unavailable'),
            (accounting_services.DateOutsideFiscalPeriod(date(2026, 10, 30)), 'fiscal_period_unavailable'),
        ]
        for error, code in cases:
            with self.assertRaises(PostingRejected) as ctx, _posting_errors():
                raise error
            self.assertEqual(ctx.exception.code, code)

    def test_missing_configuration_carries_the_issues(self):  # AC-06
        issue = accounting_services.PostingIssue('role_unconfigured', 'INVENTORY', 'Inventario', 'purchases',
                                                 'Falta configurar la cuenta «Inventario».')
        with self.assertRaises(PostingRejected) as ctx, _posting_errors():
            raise accounting_services.PostingConfigurationMissing([issue])
        self.assertEqual(ctx.exception.code, 'posting_configuration_missing')
        self.assertEqual(ctx.exception.extra['issues'][0]['role'], 'INVENTORY')


class ReceiptRepresentationTests(SimpleTestCase):
    def detail(self, entry, enabled):
        receipt = Receipt(id=uuid4(), purchase_id=uuid4(), receipt_date=TODAY, user_id=None, user_name='ana')
        purchase = SimpleNamespace(id=receipt.purchase_id, reference='COM-1')
        return ReceiptDetail(receipt, purchase, '', None, False, enabled, entry)

    def test_exposes_the_linked_entry(self):  # AC-08, API-02
        entry = PostedEntry(uuid4(), TODAY, D('58.00'))
        body = receipt_representation(self.detail(entry, True))
        self.assertEqual(body['accounting_entry'],
                         {'id': entry.id, 'accounting_date': TODAY.isoformat(), 'total': '58.00'})
        self.assertTrue(body['accounting_enabled'])

    def test_without_entry_it_is_null(self):  # AC-08, API-02
        body = receipt_representation(self.detail(None, False))
        self.assertEqual((body['accounting_entry'], body['accounting_enabled']), (None, False))


class PaymentSplitTests(SimpleTestCase):
    def test_a_payment_settles_recognized_debt_first_and_the_excess_is_an_advance(self):  # AC-15, INV-06
        self.assertEqual(split_payment(D('300'), D('1000'), D('0')), (D('300'), D('0')))
        self.assertEqual(split_payment(D('500'), D('400'), D('0')), (D('400'), D('100')))
        self.assertEqual(split_payment(D('400'), D('0'), D('0')), (D('0'), D('400')))
        self.assertEqual(split_payment(D('500'), D('1000'), D('600')), (D('400'), D('100')))

    def test_nothing_is_due_once_everything_recognized_is_paid(self):  # INV-08
        self.assertEqual(split_payment(D('100'), D('400'), D('500')), (D('0'), D('100')))

    def test_received_value_uses_the_line_price_with_line_rounding(self):  # INV-08
        purchase = purchase_of('10', '5.00')
        self.assertEqual(purchase.received_value({purchase.items[0].id: D('4')}), D('20.00'))
        self.assertEqual(purchase.received_value({}), D('0'))

    def test_a_payment_defaults_to_debt_paid_and_allocate_splits_it(self):  # AC-21, INV-06
        payment = Payment(uuid4(), uuid4(), D('500.00'), PaymentMethod.CASH, TODAY, None, 'Ana')
        self.assertEqual((payment.debt_amount, payment.advance_amount), (D('500.00'), D('0')))
        payment.allocate(D('400.00'))
        self.assertEqual((payment.debt_amount, payment.advance_amount), (D('400.00'), D('100.00')))
        with self.assertRaises(ValueError):
            payment.allocate(D('600.00'))
