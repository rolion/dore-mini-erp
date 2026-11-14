"""PB-COB-002: orden y reglas de `CollectionService` con el libro, con fakes (sin BD)."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.receivables.application.collections import CollectionService, PaymentInput
from modules.receivables.domain.obligation import ObligationStateError
from modules.receivables.tests.test_domain import snapshot

TODAY = date(2026, 11, 4)
NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)


class FakeRepository:
    def __init__(self, events):
        self.events, self.obligation, self.keys, self.payments = events, None, {}, []

    def find(self, kind, number):
        return self.obligation

    def lock_or_create(self, empty):
        self.events.append('lock_obligation')
        self.obligation = self.obligation or empty
        return self.obligation

    def find_payment_by_key(self, key):
        return self.keys.get(key)

    def next_receipt(self):
        return f'CB-{len(self.payments) + 1:06d}'

    def add_payment(self, obligation, payment, digest):
        self.events.append('add_payment')
        self.payments.append(payment)


class FakeSource:
    def __init__(self, events, snap):
        self.events, self.snap = events, snap

    def get(self, number):
        return self.snap

    def lock(self, number):
        self.events.append('lock_proforma')
        return self.snap

    def mark_collected(self, line_ids):
        self.events.append('mark_collected')
        list(line_ids)


class FakeLedger:
    def __init__(self, events, available=True, error=None):
        self.events, self.available, self.error, self.calls = events, available, error, []

    def is_available(self):
        return self.available

    def record(self, kind, number, payment, actor_id, actor_name):
        self.events.append('record')
        if self.error:
            raise self.error
        self.calls.append((kind, number, payment.amount, payment.receipt_number, actor_id))


class CollectionLedgerTests(SimpleTestCase):
    def build(self, **ledger_args):
        self.events = []
        self.snap = snapshot(amounts=(('accepted', '300.00'),))
        self.repository = FakeRepository(self.events)
        self.ledger = FakeLedger(self.events, **ledger_args)
        source = FakeSource(self.events, self.snap)
        self.service = CollectionService(self.repository, lambda kind: source, today=lambda: TODAY, now=lambda: NOW,
                                         user_id=7, user_name='ana', ledger=self.ledger)

    def data(self, amount='100.00'):
        return PaymentInput(uuid4(), Decimal(amount), 'CASH', None, '',
                            ((self.snap.lines[0].line_id, Decimal(amount)),))

    def test_entry_is_recorded_after_the_payment_and_before_marking_lines(self):  # INV-02
        self.build()
        self.service.register_payment('quotation', 'PRO-000001', self.data())
        self.assertEqual(self.events, ['lock_obligation', 'lock_proforma', 'add_payment', 'record', 'mark_collected'])
        self.assertEqual(self.ledger.calls, [('quotation', 'PRO-000001', Decimal('100.00'), 'CB-000001', 7)])

    def test_unavailable_ledger_is_never_called(self):  # AC-09
        self.build(available=False)
        self.service.register_payment('quotation', 'PRO-000001', self.data())
        self.assertNotIn('record', self.events)

    def test_ledger_failure_propagates_so_the_caller_rolls_back(self):  # AC-05, AC-06
        error = ObligationStateError('sin cuenta', 'payment_method_without_account')
        self.build(error=error)
        with self.assertRaises(ObligationStateError) as caught:
            self.service.register_payment('quotation', 'PRO-000001', self.data())
        self.assertEqual(caught.exception.code, 'payment_method_without_account')
        self.assertNotIn('mark_collected', self.events)

    def test_replay_does_not_call_the_ledger(self):  # EDGE-01
        self.build()
        data = self.data()
        result = self.service.register_payment('quotation', 'PRO-000001', data)
        row = type('Row', (), {'id': result.payment.id,
                               'obligation': type('O', (), {'source_kind': 'quotation', 'source_number': 'PRO-000001'})})
        from modules.receivables.application.collections import _digest
        self.repository.keys[data.idempotency_key] = (row, _digest('quotation', 'PRO-000001', data))
        self.events.clear()
        replay = self.service.register_payment('quotation', 'PRO-000001', data)
        self.assertTrue(replay.replayed)
        self.assertNotIn('record', self.events)
