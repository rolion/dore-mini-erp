"""API de oportunidades (AC-02…AC-09) con dos empresas, pedidos reales de Ventas y `DjangoStageCards` real."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.crm.infrastructure.django.models import (
    BoardModel,
    LeadModel,
    OpportunityModel,
    StageChangeModel,
    StageModel,
)
from modules.customers.infrastructure.django.models import CustomerModel
from modules.sales.domain.order import Order
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository

URL = '/api/crm/opportunities/'
BOARDS = '/api/crm/boards/'
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


@override_settings(DEFAULT_PHONE_COUNTRY_CODE='591')
class OpportunityApiBase(APITestCase):
    def setUp(self):
        self.company = make_company('CRM A')
        self.user = make_admin(self.company, username='crm-admin')
        authenticate(self.client, self.user)
        self.board = self.make_board('Ventas', 'Nuevo', 'Propuesta', 'Cierre')
        self.stages = [s['id'] for s in self.board['stages']]

    def make_board(self, name, *stages):
        body = self.client.post(BOARDS, {'name': name}, format='json').json()
        for stage in stages:
            body = self.client.post(f"{BOARDS}{body['id']}/stages/", {'name': stage}, format='json').json()
        return body

    def lead(self, name='Ana', phone='', company=None):
        return LeadModel.objects.create(company_id=(company or self.company).id, name=name, phone=phone,
                                        normalized_phone='')

    def customer(self, name='Cliente', phone='', active=True, company=None):
        return CustomerModel.objects.create(company_id=(company or self.company).id, name=name, phone=phone,
                                            active=active)

    def order(self, customer, total='80.00', cancelled=False, company=None):
        order = Order.create(sales_channel='WHATSAPP', order_date=date(2026, 11, 20),
                             customer_id=customer.id if customer else None)
        order.add_item(uuid4(), 'Pack', Decimal(total), 1)
        if cancelled:
            order.cancel('Ya no lo quiere', NOW)
        return DjangoOrderRepository((company or self.company).id).save(order)

    def create(self, expected=201, **data):
        payload = {'board_id': self.board['id'], 'title': 'Pack familiar', 'amount': '120.50', **data}
        response = self.client.post(URL, payload, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def post(self, opportunity_id, action, data=None, expected=200):
        response = self.client.post(f'{URL}{opportunity_id}/{action}/', data or {}, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def link(self, opportunity_id, order_id, expected=200):
        response = self.client.put(f'{URL}{opportunity_id}/order/', {'order_id': str(order_id)}, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def history(self, opportunity_id):
        response = self.client.get(f'{URL}{opportunity_id}/history/')
        self.assertEqual(response.status_code, 200, response.content)
        return [(h['from_stage_id'], h['to_stage_id']) for h in response.json()]

    def disable(self, module_key):
        from modules.modularity.infrastructure.django.models import CompanyModuleModel
        self.client.get(BOARDS)  # siembra los módulos por defecto
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key=module_key).delete()


class CreateTests(OpportunityApiBase):
    def test_create_for_lead_in_first_stage_with_initial_history(self):  # AC-02, INV-08
        lead = self.lead('Ana', phone='76543210')
        body = self.create(lead_id=str(lead.id), company_id=str(uuid4()), next_action_at='2026-11-25T15:00:00Z')
        self.assertEqual(set(body), {'id', 'board_id', 'stage_id', 'lead', 'customer', 'title', 'owner', 'amount',
                                     'currency', 'next_action_at', 'status', 'closed_at', 'order_id', 'lost_reason',
                                     'created_at'})
        self.assertEqual((body['stage_id'], body['status'], body['amount'], body['currency']),
                         (self.stages[0], 'open', '120.50', 'BOB'))
        self.assertEqual(body['lead'], {'id': str(lead.id), 'name': 'Ana', 'phone': '76543210'})
        self.assertIsNone(body['customer'])
        self.assertEqual(body['owner']['id'], self.user.id)
        self.assertIn('crm-admin', body['owner']['name'])
        stored = OpportunityModel.objects.get(pk=body['id'])
        self.assertIsNotNone(body['next_action_at'])
        self.assertEqual((stored.company_id, stored.next_action_at),
                         (self.company.id, datetime(2026, 11, 25, 15, 0, tzinfo=timezone.utc)))
        self.assertEqual(self.history(body['id']), [(None, self.stages[0])])
        self.assertEqual(StageChangeModel.objects.get(opportunity_id=body['id']).changed_by, self.user.id)

    def test_create_for_customer_in_chosen_stage_with_owner(self):  # AC-02, INV-07
        customer = self.customer('Beto', phone='+59171234567')
        colleague = make_admin(self.company, username='colega')
        body = self.create(customer_id=str(customer.id), stage_id=self.stages[1], owner_id=colleague.id)
        self.assertEqual((body['stage_id'], body['owner']['id'], body['lead']),
                         (self.stages[1], colleague.id, None))
        self.assertEqual(body['customer'], {'id': str(customer.id), 'name': 'Beto', 'phone': '+59171234567'})

    def test_converted_lead_brings_its_customer(self):  # INV-05
        customer = self.customer('Ana')
        lead = self.lead('Ana')
        LeadModel.objects.filter(pk=lead.id).update(converted_customer_id=customer.id)
        self.assertEqual(self.create(lead_id=str(lead.id))['customer']['id'], str(customer.id))

    def test_validation_errors(self):  # AC-02, AC-09, INV-07
        lead = self.lead()
        other_user = make_admin(make_company('CRM B'), username='ajeno')
        cases = [
            ({}, 'lead_id'),
            ({'lead_id': str(lead.id), 'description': 'x' * 1001}, 'description'),
            ({'lead_id': str(lead.id), 'amount': '-1'}, 'amount'),
            ({'lead_id': str(lead.id), 'amount': '1.234'}, 'amount'),
            ({'lead_id': str(lead.id), 'title': '  '}, 'title'),
            ({'lead_id': str(lead.id), 'owner_id': other_user.id}, 'owner_id'),
            ({'lead_id': str(lead.id), 'customer_id': str(self.customer('Inactivo', active=False).id)},
             'customer_id'),
        ]
        for data, field in cases:
            self.assertIn(field, self.create(expected=400, **data), data)
        self.assertEqual(OpportunityModel.objects.count(), 0)

    def test_stage_rules(self):  # AC-02, AC-03
        lead = str(self.lead().id)
        other_board = self.make_board('Postventa', 'Seguimiento')
        self.assertIn('stage_id', self.create(expected=400, lead_id=lead, stage_id=other_board['stages'][0]['id']))
        self.client.post(f"{BOARDS}{self.board['id']}/stages/{self.stages[2]}/archive/", {}, format='json')
        self.assertIn('stage_id', self.create(expected=400, lead_id=lead, stage_id=self.stages[2]))
        empty = self.make_board('Vacío')
        conflict = self.create(expected=409, lead_id=lead, board_id=empty['id'])
        self.assertEqual(conflict['code'], 'board_has_no_stages')

    def test_foreign_references_are_404(self):  # INV-01, INV-10
        other = make_company('CRM B')
        foreign_board = BoardModel.objects.create(company_id=other.id, name='Ajeno')
        foreign_stage = StageModel.objects.create(board=foreign_board, name='X', position=1)
        lead = str(self.lead().id)
        self.create(expected=404, lead_id=lead, board_id=str(foreign_board.id))
        self.create(expected=404, lead_id=lead, stage_id=str(foreign_stage.id))
        self.create(expected=404, lead_id=str(self.lead(company=other).id))
        self.create(expected=404, customer_id=str(self.customer(company=other).id))
        self.create(expected=404, customer_id=str(uuid4()))
        self.assertEqual(OpportunityModel.objects.count(), 0)


class TrackingCardTests(OpportunityApiBase):
    """Tarjeta de seguimiento = oportunidad con nombre, contacto y descripción opcional (AC-06, AC-07)."""

    def card(self, expected=201, **data):
        payload = {'board_id': self.board['id'], 'title': 'Llamar a Ana', **data}
        response = self.client.post(URL, payload, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def test_create_without_amount_nor_description(self):  # AC-06, INV-04
        body = self.card(lead_id=str(self.lead().id))
        self.assertEqual((body['amount'], body['description'], body['status']), ('0.00', '', 'open'))
        self.assertEqual(body['owner']['id'], self.user.id)
        self.assertEqual(body['stage_id'], self.stages[0])

    def test_create_with_description_and_reload(self):  # AC-06, AC-07
        customer = self.customer('Cliente Uno')
        body = self.card(customer_id=str(customer.id), description='  Pidió cotización  ', stage_id=self.stages[1])
        self.assertEqual(body['description'], 'Pidió cotización')
        listed = self.client.get(URL, {'board_id': self.board['id']}).json()['results']
        self.assertEqual([(o['title'], o['description'], o['stage_id']) for o in listed],
                         [('Llamar a Ana', 'Pidió cotización', self.stages[1])])

    def test_description_edit_and_limit(self):  # AC-07, INV-03
        body = self.card(lead_id=str(self.lead().id))
        url = f"{URL}{body['id']}/"
        edited = self.client.patch(url, {'description': 'Detalle'}, format='json').json()
        self.assertEqual(edited['description'], 'Detalle')
        self.assertEqual(self.client.patch(url, {'title': 'Otro'}, format='json').json()['description'], 'Detalle')
        too_long = self.client.patch(url, {'description': 'x' * 1001}, format='json')
        self.assertEqual(too_long.status_code, 400)
        self.assertIn('description', too_long.json())

    def test_contact_required_and_foreign_contact_404(self):  # AC-06, AC-08
        self.assertIn('lead_id', self.card(expected=400))
        other = make_company('CRM Ajena')
        self.card(expected=404, lead_id=str(self.lead(company=other).id))
        self.card(expected=404, customer_id=str(self.customer(company=other).id))

    def test_archive_empty_column_and_block_with_cards(self):  # AC-05, INV-05
        self.card(lead_id=str(self.lead().id))
        base = f"{BOARDS}{self.board['id']}/stages/"
        blocked = self.client.post(f'{base}{self.stages[0]}/archive/', {}, format='json')
        self.assertEqual((blocked.status_code, blocked.json()['code'], blocked.json()['card_count']),
                         (409, 'stage_has_cards', 1))
        empty = self.client.post(f'{base}{self.stages[2]}/archive/', {}, format='json')
        self.assertEqual(empty.status_code, 200, empty.content)
        self.assertEqual([s['id'] for s in empty.json()['stages']], self.stages[:2])


class EditMoveTests(OpportunityApiBase):
    def test_edit_open_only(self):  # INV-02
        opportunity = self.create(lead_id=str(self.lead().id))
        url = f"{URL}{opportunity['id']}/"
        body = self.client.patch(url, {'title': 'Pack grande', 'amount': '200', 'next_action_at': None},
                                 format='json').json()
        self.assertEqual((body['title'], body['amount'], body['next_action_at']), ('Pack grande', '200.00', None))
        self.assertEqual(self.client.patch(url, {'amount': '-3'}, format='json').status_code, 400)
        self.post(opportunity['id'], 'close', {'result': 'won'})
        closed = self.client.patch(url, {'title': 'Otro'}, format='json')
        self.assertEqual((closed.status_code, closed.json()['code']), (409, 'opportunity_closed'))

    def test_move_within_board_records_history(self):  # AC-03, INV-08
        opportunity = self.create(lead_id=str(self.lead().id))
        moved = self.post(opportunity['id'], 'move', {'stage_id': self.stages[2]})
        self.assertEqual(moved['stage_id'], self.stages[2])
        self.post(opportunity['id'], 'move', {'stage_id': self.stages[2]})  # misma etapa: sin registro
        self.post(opportunity['id'], 'move', {'stage_id': self.stages[1]})
        self.assertEqual(self.history(opportunity['id']),
                         [(None, self.stages[0]), (self.stages[0], self.stages[2]), (self.stages[2], self.stages[1])])

    def test_move_rejections(self):  # AC-03
        opportunity = self.create(lead_id=str(self.lead().id))
        other_board = self.make_board('Postventa', 'Seguimiento')
        self.assertIn('stage_id', self.post(opportunity['id'], 'move', {'stage_id': other_board['stages'][0]['id']},
                                            expected=400))
        self.client.post(f"{BOARDS}{self.board['id']}/stages/{self.stages[2]}/archive/", {}, format='json')
        self.post(opportunity['id'], 'move', {'stage_id': self.stages[2]}, expected=400)
        foreign = StageModel.objects.create(board=BoardModel.objects.create(company_id=make_company('X').id,
                                                                            name='Ajeno'), name='X', position=1)
        self.post(opportunity['id'], 'move', {'stage_id': str(foreign.id)}, expected=404)
        self.post(opportunity['id'], 'close', {'result': 'lost', 'lost_reason': 'Precio'})
        closed = self.post(opportunity['id'], 'move', {'stage_id': self.stages[1]}, expected=409)
        self.assertEqual(closed['code'], 'opportunity_closed')
        self.assertEqual(str(OpportunityModel.objects.get(pk=opportunity['id']).stage_id), self.stages[0])


class CloseTests(OpportunityApiBase):
    def test_lost_requires_reason_and_is_idempotent(self):  # AC-04
        opportunity = self.create(lead_id=str(self.lead().id))
        self.assertIn('lost_reason', self.post(opportunity['id'], 'close', {'result': 'lost'}, expected=400))
        self.assertIn('result', self.post(opportunity['id'], 'close', {'result': 'maybe'}, expected=400))
        first = self.post(opportunity['id'], 'close', {'result': 'lost', 'lost_reason': 'Precio alto'})
        self.assertEqual((first['status'], first['lost_reason']), ('lost', 'Precio alto'))
        self.assertIsNotNone(first['closed_at'])
        again = self.post(opportunity['id'], 'close', {'result': 'lost', 'lost_reason': 'Precio alto'})
        self.assertEqual(again['closed_at'], first['closed_at'])
        conflict = self.post(opportunity['id'], 'close', {'result': 'won'}, expected=409)
        self.assertEqual(conflict['code'], 'already_closed')

    def test_won_without_requirements_is_idempotent(self):  # AC-04
        opportunity = self.create(lead_id=str(self.lead().id))
        first = self.post(opportunity['id'], 'close', {'result': 'won'})
        self.assertEqual((first['status'], first['order_id'], first['lost_reason']), ('won', None, ''))
        again = self.post(opportunity['id'], 'close', {'result': 'won'})
        self.assertEqual(again['closed_at'], first['closed_at'])
        conflict = self.post(opportunity['id'], 'close', {'result': 'lost', 'lost_reason': 'x'}, expected=409)
        self.assertEqual(conflict['code'], 'already_closed')


class OrderLinkTests(OpportunityApiBase):
    def setUp(self):
        super().setUp()
        self.buyer = self.customer('Beto')
        self.opportunity = self.create(customer_id=str(self.buyer.id))

    def won(self, **data):
        return self.post(self.opportunity['id'], 'close', {'result': 'won', **data})

    def code(self, order_id, expected=409, opportunity_id=None):
        body = self.link(opportunity_id or self.opportunity['id'], order_id, expected=expected)
        return body.get('code')

    def test_close_won_with_order_and_link_later(self):  # AC-06
        order = self.order(self.buyer)
        self.assertEqual(self.won(order_id=str(order.id))['order_id'], str(order.id))
        self.assertEqual(self.link(self.opportunity['id'], order.id)['order_id'], str(order.id))  # idempotente
        other = self.order(self.buyer, total='15.00')
        self.assertEqual(self.link(self.opportunity['id'], other.id)['order_id'], str(other.id))

    def test_each_rejection_code(self):  # AC-06, INV-06
        order = self.order(self.buyer)
        self.assertEqual(self.code(order.id), 'opportunity_not_won')
        self.won()
        self.assertEqual(self.code(self.order(self.customer('Otro')).id), 'order_customer_mismatch')
        self.assertEqual(self.code(self.order(self.buyer, cancelled=True).id), 'order_cancelled')
        foreign_customer = self.customer('Ajeno', company=make_company('CRM B'))
        self.code(self.order(foreign_customer, company=make_company('CRM C')).id, expected=404)
        self.code(uuid4(), expected=404)
        self.link(self.opportunity['id'], order.id)
        rival = self.create(customer_id=str(self.buyer.id))
        self.post(rival['id'], 'close', {'result': 'won'})
        self.assertEqual(self.code(order.id, opportunity_id=rival['id']), 'order_already_linked')
        lead_only = self.create(lead_id=str(self.lead().id))
        self.post(lead_only['id'], 'close', {'result': 'won'})
        self.assertEqual(self.code(order.id, opportunity_id=lead_only['id']), 'customer_required')

    def test_failed_link_on_close_leaves_it_open(self):  # atómico
        cancelled = self.order(self.buyer, cancelled=True)
        body = self.post(self.opportunity['id'], 'close', {'result': 'won', 'order_id': str(cancelled.id)},
                         expected=409)
        self.assertEqual(body['code'], 'order_cancelled')
        self.assertEqual(OpportunityModel.objects.get(pk=self.opportunity['id']).status, 'open')

    def test_sales_disabled(self):  # AC-06
        order = self.order(self.buyer)
        self.won()
        self.disable('sales')
        self.assertEqual(self.code(order.id), 'sales_disabled')
        response = self.client.get(f"{URL}{self.opportunity['id']}/orders/")
        self.assertEqual((response.status_code, response.json()['code']), (409, 'sales_disabled'))

    def test_linkable_orders(self):  # AC-06
        kept = self.order(self.buyer, total='80.00')
        self.order(self.buyer, cancelled=True)
        taken = self.order(self.buyer, total='30.00')
        self.order(self.customer('Otro'))
        rival = self.create(customer_id=str(self.buyer.id))
        self.post(rival['id'], 'close', {'result': 'won', 'order_id': str(taken.id)})
        response = self.client.get(f"{URL}{self.opportunity['id']}/orders/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), [{'id': str(kept.id), 'order_date': '2026-11-20', 'total': '80.00',
                                            'status': 'NEW'}])
        lead_only = self.create(lead_id=str(self.lead().id))
        response = self.client.get(f"{URL}{lead_only['id']}/orders/")
        self.assertEqual((response.status_code, response.json()['code']), (409, 'customer_required'))


class ListTests(OpportunityApiBase):
    def test_filters(self):  # AC-07
        colleague = make_admin(self.company, username='colega')
        lead = self.lead()
        buyer = self.customer('Beto')
        a = self.create(lead_id=str(lead.id))
        b = self.create(customer_id=str(buyer.id), owner_id=colleague.id)
        c = self.create(customer_id=str(buyer.id))
        self.post(c['id'], 'close', {'result': 'lost', 'lost_reason': 'Precio'})
        other_board = self.make_board('Postventa', 'Uno')
        self.create(lead_id=str(lead.id), board_id=other_board['id'])

        def ids(**params):
            response = self.client.get(URL, {'board_id': self.board['id'], **params})
            self.assertEqual(response.status_code, 200, response.content)
            return {r['id'] for r in response.json()['results']}

        self.assertEqual(ids(), {a['id'], b['id'], c['id']})
        self.assertEqual(ids(owner_id=colleague.id), {b['id']})
        self.assertEqual(ids(lead_id=str(lead.id)), {a['id']})
        self.assertEqual(ids(customer_id=str(buyer.id)), {b['id'], c['id']})
        self.assertEqual(ids(status='open'), {a['id'], b['id']})
        self.assertEqual(ids(status='lost'), {c['id']})
        self.assertEqual(ids(lead_id=str(self.lead(company=make_company('CRM B')).id)), set())
        page = self.client.get(URL, {'board_id': self.board['id'], 'page_size': 2}).json()
        self.assertEqual((page['count'], len(page['results'])), (3, 2))
        for bad in ({}, {'board_id': 'x'}, {'board_id': self.board['id'], 'status': 'maybe'},
                    {'board_id': self.board['id'], 'owner_id': 'x'}):
            self.assertEqual(self.client.get(URL, bad).status_code, 400, bad)

    def test_list_resolves_contacts_in_batch(self):  # NFR sin N+1
        def queries():
            self.client.get(URL, {'board_id': self.board['id']})  # calienta cachés por petición
            with CaptureQueriesContext(connection) as captured:
                response = self.client.get(URL, {'board_id': self.board['id']})
            self.assertEqual(response.status_code, 200)
            return len(captured), len(response.json()['results'])

        buyer = self.customer('Beto')
        self.create(customer_id=str(buyer.id))
        self.create(lead_id=str(self.lead().id))
        few = queries()
        for _ in range(4):
            self.create(customer_id=str(self.customer('Otro').id))
            self.create(lead_id=str(self.lead().id))
        many = queries()
        self.assertEqual((few[1], many[1]), (2, 10))
        self.assertEqual(many[0], few[0])


class AccessTests(OpportunityApiBase):
    def test_other_company_opportunities_are_404_everywhere(self):  # INV-10
        other = make_company('CRM B')
        board = BoardModel.objects.create(company_id=other.id, name='Ajeno')
        stage = StageModel.objects.create(board=board, name='X', position=1)
        foreign = OpportunityModel.objects.create(company_id=other.id, board=board, stage=stage,
                                                  customer_id=uuid4(), owner_id=1, title='Ajena',
                                                  amount=Decimal('5.00'))
        base = f'{URL}{foreign.id}/'
        calls = [
            self.client.get(base), self.client.patch(base, {'title': 'x'}, format='json'),
            self.client.post(base + 'move/', {'stage_id': str(stage.id)}, format='json'),
            self.client.post(base + 'close/', {'result': 'won'}, format='json'),
            self.client.put(base + 'order/', {'order_id': str(uuid4())}, format='json'),
            self.client.get(base + 'orders/'), self.client.get(base + 'history/'),
            self.client.get(URL, {'board_id': str(board.id)}),
        ]
        self.assertEqual([c.status_code for c in calls], [404] * len(calls))
        foreign.refresh_from_db()
        self.assertEqual((foreign.status, foreign.title), ('open', 'Ajena'))

    def test_unauthenticated_company_less_and_module_disabled(self):  # AC-09
        url = f"{URL}?board_id={self.board['id']}"
        self.disable('customers')
        response = self.client.get(url)
        self.assertEqual((response.status_code, response.json()['code']), (403, 'module_disabled'))
        authenticate(self.client, get_user_model().objects.create_user(username='sin-empresa', password='x-Pass-123'))
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get(url).status_code, 401)


class BoardCardsTests(OpportunityApiBase):
    def test_card_count_counts_open_opportunities(self):  # AC-08, INV-09
        lead = str(self.lead().id)
        self.create(lead_id=lead)
        self.create(lead_id=lead)
        closed = self.create(lead_id=lead)
        self.post(closed['id'], 'close', {'result': 'won'})
        self.create(lead_id=lead, stage_id=self.stages[1])
        board = self.client.get(f"{BOARDS}{self.board['id']}/").json()
        self.assertEqual([s['card_count'] for s in board['stages']], [2, 1, 0])

    def test_archive_stage_reassigns_open_opportunities_with_history(self):  # AC-08, INV-08
        lead = str(self.lead().id)
        a = self.create(lead_id=lead)
        b = self.create(lead_id=lead)
        closed = self.create(lead_id=lead)
        self.post(closed['id'], 'close', {'result': 'lost', 'lost_reason': 'Precio'})
        url = f"{BOARDS}{self.board['id']}/stages/{self.stages[0]}/archive/"
        blocked = self.client.post(url, {}, format='json')
        self.assertEqual((blocked.status_code, blocked.json()['code'], blocked.json()['card_count']),
                         (409, 'stage_has_cards', 2))
        response = self.client.post(url, {'target_stage_id': self.stages[2]}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([(s['name'], s['card_count']) for s in response.json()['stages']],
                         [('Propuesta', 0), ('Cierre', 2)])
        for opportunity in (a, b):
            self.assertEqual(self.history(opportunity['id']),
                             [(None, self.stages[0]), (self.stages[0], self.stages[2])])
            self.assertIsNone(StageChangeModel.objects.filter(opportunity_id=opportunity['id'])
                              .order_by('-changed_at').first().changed_by)
        self.assertEqual(str(OpportunityModel.objects.get(pk=closed['id']).stage_id), self.stages[0])  # histórica

    def test_board_with_open_opportunities_cannot_be_archived(self):  # AC-08
        opportunity = self.create(lead_id=str(self.lead().id))
        response = self.client.post(f"{BOARDS}{self.board['id']}/archive/")
        self.assertEqual((response.status_code, response.json()['code']), (409, 'board_has_cards'))
        self.post(opportunity['id'], 'close', {'result': 'won'})
        self.assertEqual(self.client.post(f"{BOARDS}{self.board['id']}/archive/").status_code, 200)


class FullFlowTests(OpportunityApiBase):
    def test_inquiry_to_won_sale_with_order(self):  # flujo consulta → venta ganada → pedido
        lead = self.client.post('/api/crm/leads/', {'name': 'Ana', 'phone': '76543210'}, format='json').json()
        opportunity = self.create(lead_id=lead['id'], amount='150.00')
        self.post(opportunity['id'], 'move', {'stage_id': self.stages[1]})
        self.post(opportunity['id'], 'move', {'stage_id': self.stages[2]})
        conversion = self.client.post(f"/api/crm/leads/{lead['id']}/convert/", {}, format='json').json()
        self.assertTrue(conversion['created'])
        customer = CustomerModel.objects.get(pk=conversion['customer']['id'])
        detail = self.client.get(f"{URL}{opportunity['id']}/").json()
        self.assertEqual(detail['customer']['id'], str(customer.id))
        order = self.order(customer, total='150.00')
        orders = self.client.get(f"{URL}{opportunity['id']}/orders/").json()
        self.assertEqual([o['id'] for o in orders], [str(order.id)])
        won = self.post(opportunity['id'], 'close', {'result': 'won', 'order_id': str(order.id)})
        self.assertEqual((won['status'], won['order_id'], won['lead']['id'], won['customer']['id']),
                         ('won', str(order.id), lead['id'], str(customer.id)))
        self.assertEqual(len(self.history(opportunity['id'])), 3)
        board = self.client.get(f"{BOARDS}{self.board['id']}/").json()
        self.assertEqual(sum(s['card_count'] for s in board['stages']), 0)


class CompanyUsersTests(OpportunityApiBase):
    URL = '/api/crm/users/'

    def test_lists_only_users_of_the_company_and_filters_by_text(self):  # AC-02, INV-07, INV-01
        mate = make_admin(self.company, username='compa')
        make_admin(make_company('CRM B'), username='ajeno')
        body = self.client.get(self.URL).json()
        self.assertEqual({row['id'] for row in body}, {self.user.id, mate.id})
        self.assertEqual(set(body[0]), {'id', 'name'})
        found = self.client.get(self.URL, {'search': 'COMP'}).json()
        self.assertEqual([row['id'] for row in found], [mate.id])
        self.assertEqual(self.client.get(self.URL, {'search': 'ajeno'}).json(), [])

    def test_listed_user_can_be_assigned_as_owner(self):  # AC-02
        mate = make_admin(self.company, username='compa')
        self.assertEqual(self.create(owner_id=mate.id, customer_id=str(self.customer().id))['owner']['id'], mate.id)

    def test_requires_authentication_and_customers_module(self):
        self.client.credentials()
        self.assertEqual(self.client.get(self.URL).status_code, 401)
