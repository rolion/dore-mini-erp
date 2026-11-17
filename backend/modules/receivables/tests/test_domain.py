from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.receivables.domain.obligation import (
    Obligation, ObligationStateError, ObligationValidationError, build_statement, split_payment,
)
from shared.domain.commitment import CommitmentLine, CommitmentSnapshot, VersionData, build_snapshots

TODAY = date(2026, 11, 4)
NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
D = Decimal


def snapshot(status='presented', amounts=(('accepted', '100.00'), ('accepted', '200.00'), ('rejected', '50.00'))):
    lines = tuple(CommitmentLine(uuid4(), uuid4(), f'Servicio {i}', '', D(value), decision)
                  for i, (decision, value) in enumerate(amounts))
    return CommitmentSnapshot('quotation', 'PRO-000001', 1, status, uuid4(), 'Rosa Pérez', TODAY, lines)


def pay(obligation, snap, paid, allocations, **extra):
    data = dict(payment_method='CASH', payment_date=None, reference='', today=TODAY,
                receipt_number=f'CB-{len(obligation.payments) + 1:06d}', now=NOW,
                allocations=[(snap.lines[i].line_id, D(v)) for i, v in allocations])
    data.setdefault('amount', D(paid))
    data.update(extra)
    return obligation.register_payment(snap, **data)


class ObligationDomainTests(SimpleTestCase):
    def test_advance_then_partial_payment_leave_derived_balance(self):  # AC-01, INV-05
        snap = snapshot(amounts=(('accepted', '300.00'),))
        obligation = Obligation.open(snap)
        self.assertEqual(obligation.statement(snap).balance, D('300.00'))
        pay(obligation, snap, '100.00', [(0, '100.00')])
        self.assertEqual(obligation.statement(snap).balance, D('200.00'))
        pay(obligation, snap, '50.00', [(0, '50.00')])
        statement = obligation.statement(snap)
        self.assertEqual((statement.paid, statement.balance, statement.payment_status),
                         (D('150.00'), D('150.00'), 'partial'))

    def test_paid_when_everything_is_collected(self):
        snap = snapshot(amounts=(('accepted', '100.00'),))
        obligation = Obligation.open(snap)
        pay(obligation, snap, '100.00', [(0, '100.00')])
        self.assertEqual(obligation.statement(snap).payment_status, 'paid')

    def test_statement_separates_proposed_accepted_pending_rejected(self):  # AC-08
        snap = snapshot(amounts=(('accepted', '100.00'), ('pending', '40.00'), ('rejected', '50.00')))
        statement = build_statement(snap, [])
        self.assertEqual((statement.proposed, statement.accepted, statement.pending, statement.rejected),
                         (D('190.00'), D('100.00'), D('40.00'), D('50.00')))
        self.assertEqual([line.collectible for line in statement.lines], [True, False, False])

    def test_rejected_and_pending_lines_are_not_collectible(self):  # AC-04, INV-01
        snap = snapshot(amounts=(('accepted', '100.00'), ('rejected', '50.00'), ('pending', '20.00')))
        for index in (1, 2):
            with self.assertRaises(ObligationValidationError) as ctx:
                pay(Obligation.open(snap), snap, '10.00', [(index, '10.00')])
            self.assertIn('allocations', ctx.exception.errors)

    def test_allocations_must_add_up_to_the_amount(self):  # AC-07, INV-04
        snap = snapshot()
        with self.assertRaises(ObligationValidationError) as ctx:
            pay(Obligation.open(snap), snap, '100.00', [(0, '60.00'), (1, '30.00')])
        self.assertIn('allocations', ctx.exception.errors)

    def test_allocation_cannot_exceed_line_balance(self):  # AC-07
        snap = snapshot()
        obligation = Obligation.open(snap)
        pay(obligation, snap, '90.00', [(0, '90.00')])
        with self.assertRaises(ObligationValidationError):
            pay(obligation, snap, '20.00', [(0, '20.00')])
        self.assertEqual(len(obligation.payments), 1)

    def test_repeated_lines_and_empty_allocations_are_rejected(self):
        snap = snapshot()
        with self.assertRaises(ObligationValidationError):
            pay(Obligation.open(snap), snap, '20.00', [(0, '10.00'), (0, '10.00')])
        with self.assertRaises(ObligationValidationError):
            pay(Obligation.open(snap), snap, '20.00', [])

    def test_payment_field_validation(self):  # INV-03
        snap = snapshot()
        cases = [({'amount': D('0')}, 'amount'), ({'amount': D('1.005')}, 'amount'),
                 ({'payment_method': 'BITCOIN'}, 'payment_method'),
                 ({'payment_date': date(2026, 11, 5)}, 'payment_date'), ({'reference': 'x' * 101}, 'reference')]
        for extra, field in cases:
            with self.subTest(field=field):
                with self.assertRaises(ObligationValidationError) as ctx:
                    pay(Obligation.open(snap), snap, '10.00', [(0, '10.00')], **extra)
                self.assertIn(field, ctx.exception.errors)

    def test_only_presented_proformas_are_collectible(self):  # EDGE
        for status in ('draft', 'superseded'):
            snap = snapshot(status=status)
            with self.assertRaises(ObligationStateError):
                pay(Obligation.open(snap), snap, '10.00', [(0, '10.00')])

    def test_payment_defaults_to_today_and_trims_reference(self):
        snap = snapshot()
        payment = pay(Obligation.open(snap), snap, '10.00', [(0, '10.00')], reference='  QR 123  ')
        self.assertEqual((payment.payment_date, payment.reference), (TODAY, 'QR 123'))

    def test_lineage_keeps_payments_across_versions(self):  # AC-05
        first_line, second_line = uuid4(), uuid4()
        common = dict(number='PRO-000001', customer_id=uuid4(), customer_name='Rosa', date=TODAY)
        v1 = VersionData(version=1, status='superseded',
                         lines=((first_line, None, 'Limpieza', '', D('100.00'), 'accepted', True),), **common)
        v2 = VersionData(version=2, status='presented',
                         lines=((second_line, first_line, 'Limpieza', '', D('100.00'), 'accepted', True),), **common)
        snap_v1_presented = build_snapshots('quotation', [VersionData(
            version=1, status='presented', lines=v1.lines, number='PRO-000001', customer_id=common['customer_id'],
            customer_name='Rosa', date=TODAY)])['PRO-000001']
        obligation = Obligation.open(snap_v1_presented)
        pay(obligation, snap_v1_presented, '40.00', [(0, '40.00')])
        snap2 = build_snapshots('quotation', [v1, v2])['PRO-000001']
        self.assertEqual(snap2.version, 2)
        self.assertEqual(snap2.lines[0].lineage_id, first_line)
        statement = obligation.statement(snap2)
        self.assertEqual((statement.paid, statement.balance), (D('40.00'), D('60.00')))


class ProformaIdTests(SimpleTestCase):
    def test_snapshot_carries_the_id_of_the_current_version(self):  # AC-10 / API-01
        common = dict(number='PRO-000001', customer_id=uuid4(), customer_name='Rosa', date=TODAY, lines=())
        v1_id, v2_id = uuid4(), uuid4()
        versions = [VersionData(version=1, status='superseded', proforma_id=v1_id, **common),
                    VersionData(version=2, status='presented', proforma_id=v2_id, **common),
                    VersionData(version=3, status='draft', proforma_id=uuid4(), **common)]
        self.assertEqual(build_snapshots('quotation', versions)['PRO-000001'].proforma_id, v2_id)


class RenderedServiceDomainTests(SimpleTestCase):
    """SRV-01: prestación de tratamientos (INV-01..03, INV-04, INV-05, AC-07, AC-08, AC-11)."""

    def setUp(self):
        self.snap = snapshot()
        self.obligation = Obligation.open(self.snap)

    def render(self, index=1, **extra):
        return self.obligation.mark_rendered(self.snap, self.snap.lines[index].line_id, service_date=None,
                                             today=TODAY, now=NOW, **extra)

    def test_marking_a_line_creates_one_service_with_the_accepted_amount(self):  # INV-01, INV-02
        service, created = self.render()
        self.assertEqual((created, service.amount, service.service_date), (True, D('200.00'), TODAY))
        again, created_again = self.render()
        self.assertEqual((created_again, again.id), (False, service.id))
        self.assertEqual(len(self.obligation.rendered), 1)
        statement = self.obligation.statement(self.snap)
        self.assertEqual(statement.recognized, D('200.00'))
        self.assertEqual([(l.rendered, l.can_render) for l in statement.lines],
                         [(False, True), (True, False), (False, False)])

    def test_only_accepted_lines_of_a_presented_proforma_can_be_rendered(self):  # INV-02
        with self.assertRaises(ObligationValidationError):
            self.render(2)  # rechazada
        with self.assertRaises(ObligationValidationError):
            self.obligation.mark_rendered(self.snap, uuid4(), service_date=None, today=TODAY)
        draft = snapshot(status='draft')
        with self.assertRaises(ObligationStateError):
            Obligation.open(draft).mark_rendered(draft, draft.lines[0].line_id, service_date=None, today=TODAY)

    def test_the_service_date_is_never_in_the_future(self):  # INV-03
        with self.assertRaises(ObligationValidationError) as raised:
            self.obligation.mark_rendered(self.snap, self.snap.lines[0].line_id, service_date=date(2026, 11, 5),
                                          today=TODAY)
        self.assertIn('service_date', raised.exception.errors)
        service, _ = self.obligation.mark_rendered(self.snap, self.snap.lines[0].line_id,
                                                   service_date=date(2026, 11, 1), today=TODAY)
        self.assertEqual(service.service_date, date(2026, 11, 1))

    def test_applied_to_sums_what_was_paid_to_the_line(self):  # INV-05
        pay(self.obligation, self.snap, '80.00', [(1, '80.00')])
        pay(self.obligation, self.snap, '30.00', [(1, '20.00'), (0, '10.00')])
        self.assertEqual(self.obligation.applied_to(self.snap.lines[1].lineage_id), D('100.00'))

    def test_a_payment_is_split_by_the_state_of_its_lines(self):  # INV-04, AC-07
        payment = pay(self.obligation, self.snap, '90.00', [(0, '30.00'), (1, '60.00')])
        a, b = (line.lineage_id for line in self.snap.lines[:2])
        portions = split_payment(payment, rendered={a}, recognized={a})
        self.assertEqual((portions.settlement, portions.advance, portions.rendered_unposted),
                         (D('30.00'), D('60.00'), D('0.00')))
        portions = split_payment(payment, rendered={a, b}, recognized={a})
        self.assertEqual((portions.settlement, portions.advance, portions.rendered_unposted),
                         (D('30.00'), D('0.00'), D('60.00')))
        portions = split_payment(payment, rendered=set(), recognized=set())
        self.assertEqual((portions.settlement, portions.advance, portions.rendered_unposted),
                         (D('0.00'), D('90.00'), D('0.00')))
