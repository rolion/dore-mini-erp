"""Dominio puro de prospectos y oportunidades: INV-01…INV-04 e INV-07 del PLAN."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from modules.crm.domain.errors import CrmConflict, CrmValidationError
from modules.crm.domain.lead import Lead
from modules.crm.domain.opportunity import LOST, OPEN, WON, Opportunity

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def make(**overrides) -> Opportunity:
    values = {'board_id': uuid4(), 'stage_id': uuid4(), 'lead_id': uuid4(), 'customer_id': None,
              'title': 'Pack familiar', 'amount': Decimal('120.50'), 'owner_id': 7}
    values.update(overrides)
    return Opportunity.create(**values)


class OpportunityCreateTests(TestCase):
    def test_needs_lead_or_customer(self):  # INV-01
        with self.assertRaises(CrmValidationError) as ctx:
            make(lead_id=None, customer_id=None)
        self.assertIn('lead_id', ctx.exception.errors)
        self.assertEqual(make(lead_id=None, customer_id=uuid4()).lead_id, None)
        both = make(customer_id=uuid4())
        self.assertIsNotNone(both.lead_id)
        self.assertIsNotNone(both.customer_id)

    def test_starts_open_in_bob_with_trimmed_title(self):  # INV-03, INV-07
        opportunity = make(title='  Pack  ')
        self.assertEqual((opportunity.status, opportunity.currency, opportunity.title), (OPEN, 'BOB', 'Pack'))
        self.assertIsNone(opportunity.closed_at)

    def test_amount_rules(self):  # INV-07
        self.assertEqual(make(amount='10').amount, Decimal('10.00'))
        self.assertEqual(make(amount=Decimal('0')).amount, Decimal('0.00'))
        for bad in (Decimal('-1'), Decimal('1.234'), 'abc', 10.5, Decimal('10000000000')):
            with self.assertRaises(CrmValidationError, msg=repr(bad)) as ctx:
                make(amount=bad)
            self.assertIn('amount', ctx.exception.errors)

    def test_omitted_amount_is_zero(self):  # INV-04 (TASK crm-tableros-seguimiento-comercial)
        opportunity = make(amount=None)
        self.assertEqual(opportunity.amount, Decimal('0.00'))
        self.assertIsInstance(opportunity.amount, Decimal)

    def test_description_is_optional_trimmed_and_limited(self):  # INV-03
        self.assertEqual(make().description, '')
        self.assertEqual(make(description='  Quiere pack  ').description, 'Quiere pack')
        self.assertEqual(make(description=None).description, '')
        with self.assertRaises(CrmValidationError) as ctx:
            make(description='x' * 1001)
        self.assertIn('description', ctx.exception.errors)
        opportunity = make()
        opportunity.edit(description=' Nueva ')
        self.assertEqual(opportunity.description, 'Nueva')
        opportunity.edit(title='Otro')
        self.assertEqual(opportunity.description, 'Nueva')  # sin indicar, no cambia

    def test_collects_title_and_amount_errors(self):
        with self.assertRaises(CrmValidationError) as ctx:
            make(title=' ', amount=Decimal('-5'))
        self.assertEqual(set(ctx.exception.errors), {'title', 'amount'})


class OpportunityMoveTests(TestCase):
    def test_moves_only_to_active_stage_of_same_board(self):  # INV-02
        opportunity = make()
        start, target = opportunity.stage_id, uuid4()
        self.assertEqual(opportunity.move_to(target, {start, target}), start)
        self.assertEqual(opportunity.stage_id, target)
        self.assertIsNone(opportunity.move_to(target, {start, target}))  # misma etapa: sin cambio
        with self.assertRaises(CrmValidationError):
            opportunity.move_to(uuid4(), {start, target})

    def test_closed_cannot_move_or_edit(self):  # INV-02
        opportunity = make()
        opportunity.close_won(NOW)
        with self.assertRaises(CrmConflict) as ctx:
            opportunity.move_to(uuid4(), set())
        self.assertEqual(ctx.exception.code, 'opportunity_closed')
        with self.assertRaises(CrmConflict):
            opportunity.edit(title='Otro')

    def test_edit_changes_only_given_fields(self):
        opportunity = make()
        later = NOW + timedelta(days=1)
        opportunity.edit(amount='99.90', next_action_at=later, change_next_action=True)
        self.assertEqual((opportunity.title, opportunity.amount, opportunity.next_action_at),
                         ('Pack familiar', Decimal('99.90'), later))
        opportunity.edit(change_next_action=True)
        self.assertIsNone(opportunity.next_action_at)


class OpportunityCloseTests(TestCase):
    def test_won_is_idempotent(self):  # INV-03
        opportunity = make()
        self.assertTrue(opportunity.close_won(NOW))
        self.assertFalse(opportunity.close_won(NOW + timedelta(hours=1)))
        self.assertEqual((opportunity.status, opportunity.closed_at), (WON, NOW))

    def test_lost_requires_reason_and_is_idempotent(self):  # INV-03
        opportunity = make()
        for reason in ('', '   ', None, 'x' * 501):
            with self.assertRaises(CrmValidationError):
                opportunity.close_lost(reason, NOW)
        self.assertEqual(opportunity.status, OPEN)
        self.assertTrue(opportunity.close_lost(' Precio ', NOW))
        self.assertFalse(opportunity.close_lost('Otro motivo', NOW + timedelta(hours=1)))
        self.assertEqual((opportunity.status, opportunity.lost_reason, opportunity.closed_at), (LOST, 'Precio', NOW))

    def test_other_result_on_closed_is_conflict(self):  # INV-03
        won, lost = make(), make()
        won.close_won(NOW)
        lost.close_lost('Precio', NOW)
        for call in (lambda: won.close_lost('Precio', NOW), lambda: lost.close_won(NOW)):
            with self.assertRaises(CrmConflict) as ctx:
                call()
            self.assertEqual(ctx.exception.code, 'already_closed')


class OpportunityOrderTests(TestCase):
    def test_link_rules(self):  # INV-06
        customer = uuid4()
        opportunity = make(customer_id=customer)
        order = uuid4()
        with self.assertRaises(CrmConflict) as ctx:
            opportunity.link_order(order, customer, False)
        self.assertEqual(ctx.exception.code, 'opportunity_not_won')
        opportunity.close_won(NOW)
        for args, code in (((order, uuid4(), False), 'order_customer_mismatch'),
                           ((order, customer, True), 'order_cancelled')):
            with self.assertRaises(CrmConflict) as ctx:
                opportunity.link_order(*args)
            self.assertEqual(ctx.exception.code, code)
        self.assertTrue(opportunity.link_order(order, customer, False))
        self.assertFalse(opportunity.link_order(order, customer, False))
        self.assertEqual(opportunity.order_id, order)

    def test_lead_only_requires_customer(self):  # INV-06
        opportunity = make()
        opportunity.close_won(NOW)
        with self.assertRaises(CrmConflict) as ctx:
            opportunity.link_order(uuid4(), uuid4(), False)
        self.assertEqual(ctx.exception.code, 'customer_required')

    def test_attach_customer_only_on_open_without_customer(self):  # INV-05
        customer = uuid4()
        opportunity = make()
        self.assertTrue(opportunity.attach_customer(customer))
        self.assertFalse(opportunity.attach_customer(uuid4()))
        self.assertEqual(opportunity.customer_id, customer)
        closed = make()
        closed.close_won(NOW)
        self.assertFalse(closed.attach_customer(customer))


class LeadTests(TestCase):
    def test_create_validates_and_trims(self):
        lead = Lead.create('  Ana  ', ' 76543210 ', ' ana@example.com ', normalized_phone='+59176543210')
        self.assertEqual((lead.name, lead.phone, lead.email, lead.normalized_phone),
                         ('Ana', '76543210', 'ana@example.com', '+59176543210'))
        self.assertEqual(Lead.create('Beto', '', '', normalized_phone='+591').normalized_phone, '')
        with self.assertRaises(CrmValidationError) as ctx:
            Lead.create(' ', 'x' * 31, 'no-es-correo')
        self.assertEqual(set(ctx.exception.errors), {'name', 'phone', 'email'})

    def test_converts_once(self):  # INV-04
        lead = Lead.create('Ana')
        customer = uuid4()
        self.assertTrue(lead.convert_to(customer))
        self.assertFalse(lead.convert_to(customer))
        with self.assertRaises(CrmConflict) as ctx:
            lead.convert_to(uuid4())
        self.assertEqual(ctx.exception.code, 'already_converted')
        self.assertEqual(lead.converted_customer_id, customer)
