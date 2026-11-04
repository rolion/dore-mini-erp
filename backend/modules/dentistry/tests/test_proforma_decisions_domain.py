from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.dentistry.domain.proforma import (
    ACCEPTED, KIND_CARRIED, KIND_DECISION, KIND_RECTIFICATION, LINE_ADDITIONAL, LINE_CARRIED, LINE_REPLACEMENT,
    PARTIALLY_ACCEPTED, PENDING, REJECTED, DentalProforma, DentalProformaLine, DentalProformaStateError, DentalProformaValidationError,
)

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


def line(price='100'):
    return DentalProformaLine(uuid4(), uuid4(), 'Consulta', Decimal('1'), Decimal(price))


def presented(prices=('100', '200')):
    proforma = DentalProforma.create(number='PRO-000001', customer_id=uuid4(), patient_name='Ana',
                               date=date(2026, 11, 3), lines=[line(p) for p in prices])
    proforma.present()
    return proforma


def accept(proforma, indexes, **extra):
    data = {'accepted_by_name': 'Ana Paz', 'medium': 'in_person', **extra}
    proforma.decide([proforma.lines[i].id for i in indexes], ACCEPTED, now=NOW, **data)


class ProformaDecisionTests(SimpleTestCase):
    def test_accept_first_reject_second_totals_and_status(self):  # AC-01 / INV-06
        proforma = presented()
        accept(proforma, [0])
        proforma.decide([proforma.lines[1].id], REJECTED, now=NOW, reason='Muy caro')
        self.assertEqual(proforma.totals, {'proposed': Decimal('300.00'), 'accepted': Decimal('100.00'),
                                           'pending': Decimal('0.00'), 'rejected': Decimal('200.00')})
        self.assertEqual(proforma.acceptance_status, PARTIALLY_ACCEPTED)
        self.assertEqual([l.decision for l in proforma.lines], [ACCEPTED, REJECTED])

    def test_acceptance_status_for_every_combination(self):  # AC-07
        proforma = presented()
        self.assertEqual(proforma.acceptance_status, PENDING)
        accept(proforma, [0])
        self.assertEqual(proforma.acceptance_status, PARTIALLY_ACCEPTED)
        accept(proforma, [1])
        self.assertEqual(proforma.acceptance_status, ACCEPTED)
        rejected = presented()
        rejected.decide([l.id for l in rejected.lines], REJECTED, now=NOW)
        self.assertEqual(rejected.acceptance_status, REJECTED)
        mixed = presented()
        mixed.decide([mixed.lines[0].id], REJECTED, now=NOW)
        self.assertEqual(mixed.acceptance_status, PENDING)

    def test_decisions_need_a_presented_proforma(self):  # INV-01 / AC-04
        draft = DentalProforma.create(number='X', customer_id=uuid4(), patient_name='A', date=date(2026, 11, 3),
                                lines=[line()])
        with self.assertRaises(DentalProformaStateError):
            draft.decide([draft.lines[0].id], REJECTED, now=NOW)
        old = presented()
        old.supersede()
        with self.assertRaises(DentalProformaStateError):
            old.decide([old.lines[0].id], REJECTED, now=NOW)
        self.assertEqual([l.decision for l in presented().lines], [PENDING, PENDING])  # presentar no acepta

    def test_validation_of_fields_and_lines(self):  # INV-03 / AC-05
        proforma = presented()
        first = [proforma.lines[0].id]
        for kwargs in ({}, {'accepted_by_name': 'Ana'}, {'medium': 'in_person'},
                       {'accepted_by_name': 'Ana', 'medium': 'carrier_pigeon'},
                       {'accepted_by_name': 'A' * 121, 'medium': 'phone'},
                       {'accepted_by_name': 'Ana', 'medium': 'phone', 'reference': 'x' * 201},
                       {'accepted_by_name': 'Ana', 'medium': 'phone', 'reason': 'x' * 501}):
            with self.assertRaises(DentalProformaValidationError, msg=kwargs):
                proforma.decide(first, ACCEPTED, now=NOW, **kwargs)
        for ids in ([], [first[0], first[0]], [uuid4()]):
            with self.assertRaises(DentalProformaValidationError):
                proforma.decide(ids, REJECTED, now=NOW)
        with self.assertRaises(DentalProformaValidationError):
            proforma.decide(first, 'maybe', now=NOW)
        self.assertEqual(proforma.acceptance_status, PENDING)

    def test_batch_is_all_or_nothing_and_decisions_are_never_overwritten(self):  # AC-02 / INV-04
        proforma = presented()
        accept(proforma, [0])
        with self.assertRaises(DentalProformaStateError):
            proforma.decide([l.id for l in proforma.lines], REJECTED, now=NOW)
        self.assertEqual([l.decision for l in proforma.lines], [ACCEPTED, PENDING])
        self.assertEqual(len(proforma.lines[0].decisions), 1)

    def test_rectification_keeps_both_records(self):  # AC-06 / INV-05
        proforma = presented()
        accept(proforma, [0])
        line_id = proforma.lines[0].id
        with self.assertRaises(DentalProformaValidationError):
            proforma.rectify(line_id, REJECTED, now=NOW)
        with self.assertRaises(DentalProformaStateError):
            proforma.rectify(line_id, ACCEPTED, now=NOW, reason='x', accepted_by_name='Ana', medium='phone')
        with self.assertRaises(DentalProformaStateError):
            proforma.rectify(proforma.lines[1].id, REJECTED, now=NOW, reason='x')
        proforma.rectify(line_id, REJECTED, now=NOW, reason='Se arrepintió', recorded_by=7, recorded_by_name='Admin')
        records = proforma.lines[0].decisions
        self.assertEqual([(r.kind, r.decision) for r in records],
                         [(KIND_DECISION, ACCEPTED), (KIND_RECTIFICATION, REJECTED)])
        self.assertEqual((records[1].reason, records[1].recorded_by), ('Se arrepintió', 7))
        self.assertEqual(proforma.totals['accepted'], Decimal('0.00'))
        with self.assertRaises(DentalProformaValidationError):
            proforma.rectify(line_id, ACCEPTED, now=NOW, reason='Vuelve')


class ProformaVersioningTests(SimpleTestCase):
    def v2_draft(self):
        v1 = presented()
        accept(v1, [0])
        v1.decide([v1.lines[1].id], REJECTED, now=NOW)
        return v1, v1.new_version()

    def save(self, v2, v1, lines):
        v2.replace_content(patient_name='Ana', date=v2.date, valid_until=None,
                           notes='', lines=lines, origins={l.id: l for l in v1.lines})

    def test_new_version_links_origin_and_carries_decisions(self):  # AC-08
        v1, v2 = self.v2_draft()
        self.assertEqual([l.origin_line_id for l in v2.lines], [l.id for l in v1.lines])
        self.assertEqual([(l.line_kind, l.decision) for l in v2.lines],
                         [(LINE_CARRIED, ACCEPTED), (LINE_CARRIED, REJECTED)])
        self.assertEqual(v2.totals['accepted'], Decimal('100.00'))
        self.assertEqual(v2.lines[0].decisions[0].kind, KIND_CARRIED)
        self.assertEqual(v2.lines[0].decisions[0].source_decision_id, v1.lines[0].decisions[0].id)

    def test_editing_rejected_line_makes_replacement_and_reverting_restores_it(self):
        v1, v2 = self.v2_draft()
        self.save(v2, v1, [v2.lines[0], replace(v2.lines[1], unit_price=Decimal('150'))])
        self.assertEqual((v2.lines[1].line_kind, v2.lines[1].decision), (LINE_REPLACEMENT, PENDING))
        self.assertEqual(v2.totals['pending'], Decimal('150.00'))
        self.save(v2, v1, [v2.lines[0], replace(v2.lines[1], unit_price=Decimal('200'))])
        self.assertEqual((v2.lines[1].line_kind, v2.lines[1].decision), (LINE_CARRIED, REJECTED))

    def test_new_lines_are_additional_and_saving_keeps_carried_records(self):
        v1, v2 = self.v2_draft()
        before = v2.lines[0].decisions
        self.save(v2, v1, [*v2.lines, line('50')])
        self.assertEqual(v2.lines[2].line_kind, LINE_ADDITIONAL)
        self.assertEqual(v2.lines[0].decisions, before)

    def test_accepted_inherited_line_cannot_be_edited_or_removed(self):  # INV-07
        v1, v2 = self.v2_draft()
        with self.assertRaises(DentalProformaStateError):
            self.save(v2, v1, [v2.lines[1]])
        with self.assertRaises(DentalProformaStateError):
            self.save(v2, v1, [replace(v2.lines[0], quantity=Decimal('2')), v2.lines[1]])
        self.assertEqual(len(v2.lines), 2)

    def test_rectifying_before_new_version_unlocks_the_commitment(self):
        v1 = presented()
        accept(v1, [0])
        v1.rectify(v1.lines[0].id, REJECTED, now=NOW, reason='Cambio de opinión')
        v2 = v1.new_version()
        self.assertEqual(v2.lines[0].decision, REJECTED)
        self.save(v2, v1, [])

    def test_superseded_version_keeps_its_decisions_read_only(self):  # AC-09
        v1, v2 = self.v2_draft()
        v2.present()
        v1.supersede()
        self.assertEqual(v1.totals['accepted'], Decimal('100.00'))
        with self.assertRaises(DentalProformaStateError):
            v1.decide([v1.lines[0].id], REJECTED, now=NOW)
        with self.assertRaises(DentalProformaStateError):
            v1.rectify(v1.lines[0].id, REJECTED, now=NOW, reason='x')
