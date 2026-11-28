"""Bandeja de WhatsApp (PB-CRM-012, AC-01…AC-10) con proveedor simulado, dos empresas y el webhook real."""
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.crm.infrastructure.django.models import LeadModel
from modules.customers.infrastructure.django.models import CustomerModel
from modules.messaging.domain.errors import PermanentGatewayError
from modules.messaging.infrastructure.django.models import ConversationModel, MessageModel, TemplateModel
from modules.messaging.infrastructure.fake_gateway import FakeMessagingGateway
from modules.messaging.infrastructure.worker import deliver_next_message, process_all
from modules.messaging.tests.test_api import MessagingBase, inbound_payload, status_payload

INBOX = '/api/crm/inbox/conversations/'
BOARDS = '/api/crm/boards/'
OPPORTUNITIES = '/api/crm/opportunities/'
ANA, BETO = '59176543210', '59171112222'


@override_settings(DEFAULT_PHONE_COUNTRY_CODE='591')
class InboxBase(MessagingBase):
    def receive(self, wamid, sender=ANA):
        self.assertEqual(self.post_webhook(inbound_payload(wamid=wamid, sender=sender)).status_code, 200)
        process_all()

    def conv(self, phone=ANA) -> str:
        return str(ConversationModel.objects.get(company_id=self.company.id, phone=phone).id)

    def url(self, conversation_id, tail=''):
        return f'{INBOX}{conversation_id}/{tail}'

    def customer(self, name='Cliente', phone='', active=True, company=None):
        return CustomerModel.objects.create(company_id=(company or self.company).id, name=name, phone=phone,
                                            active=active)

    def lead(self, name='Lia', phone='', normalized='', company=None):
        return LeadModel.objects.create(company_id=(company or self.company).id, name=name, phone=phone,
                                        normalized_phone=normalized)

    def board(self):
        body = self.client.post(BOARDS, {'name': 'Ventas'}, format='json').json()
        return self.client.post(f"{BOARDS}{body['id']}/stages/", {'name': 'Nuevo'}, format='json').json()

    def opportunity(self, **contact):
        board = self.board()
        payload = {'board_id': board['id'], 'title': 'Pack', 'amount': '10.00', **contact}
        response = self.client.post(OPPORTUNITIES, payload, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def other_company_client(self):
        company = make_company('Empresa Dos')
        client = APIClient()
        authenticate(client, make_admin(company, 'beto'))
        return company, client


class ListAndThreadTests(InboxBase):
    def test_list_orders_by_last_message_and_previews_it(self):  # AC-01
        self.receive('wamid.A', ANA)
        self.receive('wamid.B', BETO)
        body = self.client.get(INBOX).json()
        self.assertEqual([r['phone'] for r in body['results']], [BETO, ANA])
        first = body['results'][0]
        self.assertEqual((first['last_message']['preview'], first['last_message']['direction'], first['window_open']),
                         ('hola', 'in', True))
        self.assertEqual(body['count'], 2)

    def test_filters_by_scope_search_and_opportunity(self):  # AC-01
        self.receive('wamid.A', ANA)
        self.receive('wamid.B', BETO)
        ana = self.conv(ANA)
        self.client.put(self.url(ana, 'owner/'), {'owner_id': self.admin.id}, format='json')
        mine = self.client.get(INBOX, {'scope': 'mine'}).json()['results']
        self.assertEqual([r['phone'] for r in mine], [ANA])
        free = self.client.get(INBOX, {'scope': 'unassigned'}).json()['results']
        self.assertEqual([r['phone'] for r in free], [BETO])
        self.assertEqual(self.client.get(INBOX, {'scope': 'otro'}).status_code, 400)
        self.assertEqual([r['phone'] for r in self.client.get(INBOX, {'search': '1112'}).json()['results']], [BETO])
        customer = self.customer('Ana Cliente', phone='+59170000001')
        self.client.put(self.url(ana, 'contact/'), {'customer_id': str(customer.id)}, format='json')
        found = self.client.get(INBOX, {'search': 'Ana Cli'}).json()['results']
        self.assertEqual([r['phone'] for r in found], [ANA])
        self.assertEqual(found[0]['contact']['name'], 'Ana Cliente')
        opportunity = self.opportunity(customer_id=str(customer.id))
        self.client.put(self.url(ana, 'opportunity/'), {'opportunity_id': opportunity['id']}, format='json')
        linked = self.client.get(INBOX, {'opportunity_id': opportunity['id']}).json()['results']
        self.assertEqual([r['phone'] for r in linked], [ANA])

    def test_thread_is_chronological_and_after_returns_only_newer(self):  # AC-02
        self.receive('wamid.A')
        self.receive('wamid.B')
        conversation = self.conv()
        rows = self.client.get(self.url(conversation, 'messages/')).json()['results']
        self.assertEqual(len(rows), 2)
        self.assertLess(rows[0]['created_at'], rows[1]['created_at'])
        newer = self.client.get(self.url(conversation, 'messages/'), {'after': rows[1]['created_at']}).json()
        self.assertEqual([r['id'] for r in newer['results']], [rows[1]['id']])
        self.assertEqual(self.client.get(self.url(conversation, 'messages/'), {'after': 'x'}).status_code, 400)

    def test_detail_reports_window_and_connection(self):  # AC-02
        self.receive('wamid.A')
        body = self.client.get(self.url(self.conv())).json()
        self.assertEqual((body['window_open'], body['connection_active']), (True, True))


class ReplyTests(InboxBase):
    def test_text_inside_window_is_queued_then_delivered(self):  # AC-03
        self.receive('wamid.A')
        conversation = self.conv()
        response = self.client.post(self.url(conversation, 'messages/'), {'type': 'text', 'body': 'Hola Ana'},
                                    format='json')
        self.assertEqual((response.status_code, response.json()['status']), (202, 'queued'))
        deliver_next_message()
        self.assertEqual(FakeMessagingGateway.sent[0][:2], ('text', ANA))
        last = self.client.get(self.url(conversation)).json()['last_message']
        self.assertEqual((last['preview'], last['direction'], last['status']), ('Hola Ana', 'out', 'sent'))

    def test_text_outside_window_is_409_but_approved_template_is_allowed(self):  # AC-03
        self.receive('wamid.A')
        ConversationModel.objects.update(last_inbound_at=timezone.now() - timedelta(hours=25))
        conversation = self.conv()
        closed = self.client.post(self.url(conversation, 'messages/'), {'type': 'text', 'body': 'Hola'}, format='json')
        self.assertEqual((closed.status_code, closed.json()['code']), (409, 'window_closed'))
        self.assertFalse(self.client.get(self.url(conversation)).json()['window_open'])
        approved = TemplateModel.objects.create(company_id=self.company.id, connection=self.connection, name='hi',
                                                language='es', category='UTILITY', status='APPROVED',
                                                synced_at=timezone.now())
        ok = self.client.post(self.url(conversation, 'messages/'),
                              {'type': 'template', 'template_id': str(approved.id)}, format='json')
        self.assertEqual(ok.status_code, 202)
        rejected = TemplateModel.objects.create(company_id=self.company.id, connection=self.connection, name='no',
                                                language='es', category='UTILITY', status='REJECTED',
                                                synced_at=timezone.now())
        bad = self.client.post(self.url(conversation, 'messages/'),
                               {'type': 'template', 'template_id': str(rejected.id)}, format='json')
        self.assertEqual((bad.status_code, bad.json()['code']), (409, 'template_not_approved'))

    def test_input_shape_is_validated(self):  # AC-03
        self.receive('wamid.A')
        conversation = self.conv()
        for payload in ({'type': 'text'}, {'type': 'template'}, {'type': 'video'}):
            self.assertEqual(self.client.post(self.url(conversation, 'messages/'), payload, format='json').status_code,
                             400)

    def test_failed_send_shows_reason_and_can_be_retried(self):  # AC-04
        self.receive('wamid.A')
        conversation = self.conv()
        sent = self.client.post(self.url(conversation, 'messages/'), {'type': 'text', 'body': 'Hola'}, format='json')
        message_id = sent.json()['id']
        FakeMessagingGateway.failures = [PermanentGatewayError('400 número inválido')]
        deliver_next_message()
        failed = self.client.get(self.url(conversation, 'messages/')).json()['results'][-1]
        self.assertEqual((failed['status'], failed['failure_reason']), ('failed', '400 número inválido'))
        retried = self.client.post(self.url(conversation, f'messages/{message_id}/retry/'))
        self.assertEqual((retried.status_code, retried.json()['status']), (202, 'queued'))
        deliver_next_message()
        self.assertEqual(MessageModel.objects.get(id=message_id).status, 'sent')
        again = self.client.post(self.url(conversation, f'messages/{message_id}/retry/'))
        self.assertEqual((again.status_code, again.json()['code']), (409, 'not_retryable'))

    def test_retry_of_text_needs_an_open_window(self):  # INV-08
        self.receive('wamid.A')
        conversation = self.conv()
        message_id = self.client.post(self.url(conversation, 'messages/'), {'type': 'text', 'body': 'Hola'},
                                      format='json').json()['id']
        FakeMessagingGateway.failures = [PermanentGatewayError('400')]
        deliver_next_message()
        ConversationModel.objects.update(last_inbound_at=timezone.now() - timedelta(hours=30))
        response = self.client.post(self.url(conversation, f'messages/{message_id}/retry/'))
        self.assertEqual((response.status_code, response.json()['code']), (409, 'window_closed'))
        self.assertEqual(MessageModel.objects.get(id=message_id).status, 'failed')

    def test_retry_of_unknown_message_is_404(self):
        self.receive('wamid.A')
        response = self.client.post(self.url(self.conv(), 'messages/00000000-0000-0000-0000-000000000001/retry/'))
        self.assertEqual(response.status_code, 404)


class WebhookThroughInboxTests(InboxBase):
    def test_bad_signature_repeated_event_and_out_of_order_status(self):  # AC-09
        self.assertEqual(self.post_webhook(inbound_payload(), secret='otra-clave').status_code, 401)
        self.assertEqual(self.client.get(INBOX).json()['count'], 0)
        self.receive('wamid.A')
        self.receive('wamid.A')  # el mismo wamid dos veces
        conversation = self.conv()
        self.assertEqual(len(self.client.get(self.url(conversation, 'messages/')).json()['results']), 1)
        self.client.post(self.url(conversation, 'messages/'), {'type': 'text', 'body': 'Hola'}, format='json')
        deliver_next_message()
        wamid = MessageModel.objects.get(direction='out').provider_message_id
        for status in ('read', 'delivered'):  # fuera de orden: delivered no retrocede a read
            self.post_webhook(status_payload(wamid, status))
            process_all()
        out = [m for m in self.client.get(self.url(conversation, 'messages/')).json()['results']
               if m['direction'] == 'out']
        self.assertEqual(out[0]['status'], 'read')


class AssignAndLinkTests(InboxBase):
    def setUp(self):
        super().setUp()
        self.receive('wamid.A')
        self.conversation = self.conv()

    def put(self, tail, data, expected=200):
        response = self.client.put(self.url(self.conversation, tail), data, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def test_assign_unassign_and_foreign_user(self):  # AC-05, INV-02
        self.assertEqual(self.put('owner/', {'owner_id': self.admin.id})['owner']['id'], self.admin.id)
        self.assertIsNone(self.put('owner/', {'owner_id': None})['owner'])
        foreign = make_admin(make_company('Ajena'), 'zoe')
        self.put('owner/', {'owner_id': foreign.id}, expected=400)
        self.put('owner/', {}, expected=400)

    def test_contact_link_replace_remove_and_errors(self):  # AC-06, INV-03, INV-04
        customer, lead = self.customer('Ana'), self.lead('Lia')
        body = self.put('contact/', {'customer_id': str(customer.id)})
        self.assertEqual(body['contact'], {'type': 'customer', 'id': str(customer.id), 'name': 'Ana'})
        self.assertEqual(self.put('contact/', {'lead_id': str(lead.id)})['contact']['type'], 'lead')
        self.put('contact/', {'customer_id': str(customer.id), 'lead_id': str(lead.id)}, expected=400)
        self.assertIsNone(self.put('contact/', {})['contact'])
        inactive = self.customer('Baja', active=False)
        self.assertEqual(self.put('contact/', {'customer_id': str(inactive.id)}, expected=409)['code'],
                         'customer_inactive')
        other_company, _ = self.other_company_client()
        foreign = self.customer('Ajeno', company=other_company)
        self.put('contact/', {'customer_id': str(foreign.id)}, expected=404)
        self.put('contact/', {'lead_id': str(self.lead('Ajena', company=other_company).id)}, expected=404)

    def test_converted_lead_is_shown_as_its_customer(self):  # EDGE
        customer = self.customer('Ana Cliente')
        lead = self.lead('Ana Lead')
        LeadModel.objects.filter(pk=lead.id).update(converted_customer_id=customer.id)
        body = self.put('contact/', {'lead_id': str(lead.id)})
        self.assertEqual(body['contact'], {'type': 'customer', 'id': str(customer.id), 'name': 'Ana Cliente'})

    def test_link_opportunity_inherits_contact_and_checks_consistency(self):  # AC-07, INV-05
        customer, other = self.customer('Ana'), self.customer('Otro')
        opportunity = self.opportunity(customer_id=str(customer.id))
        body = self.put('opportunity/', {'opportunity_id': opportunity['id']})
        self.assertEqual((body['contact']['id'], body['opportunity']['id']), (str(customer.id), opportunity['id']))
        self.put('contact/', {'customer_id': str(other.id)})  # INV-06: cambia el contacto → se desvincula
        self.assertIsNone(self.client.get(self.url(self.conversation)).json()['opportunity'])
        self.assertEqual(self.put('opportunity/', {'opportunity_id': opportunity['id']}, expected=409)['code'],
                         'contact_mismatch')

    def test_link_for_lead_opportunity_and_unlink(self):  # AC-07
        lead = self.lead('Lia')
        opportunity = self.opportunity(lead_id=str(lead.id))
        body = self.put('opportunity/', {'opportunity_id': opportunity['id']})
        self.assertEqual(body['contact']['type'], 'lead')
        self.assertIsNone(self.put('opportunity/', {'opportunity_id': None})['opportunity'])
        listed = self.client.get(self.url(self.conversation, 'opportunities/')).json()['results']
        self.assertEqual([o['id'] for o in listed], [opportunity['id']])

    def test_closed_or_foreign_opportunity_cannot_be_linked(self):  # AC-07
        customer = self.customer('Ana')
        opportunity = self.opportunity(customer_id=str(customer.id))
        self.client.post(f"{OPPORTUNITIES}{opportunity['id']}/close/", {'result': 'lost', 'lost_reason': 'caro'},
                         format='json')
        self.assertEqual(self.put('opportunity/', {'opportunity_id': opportunity['id']}, expected=409)['code'],
                         'opportunity_closed')
        self.put('opportunity/', {'opportunity_id': '00000000-0000-0000-0000-000000000009'}, expected=404)

    def test_create_opportunity_from_conversation(self):  # AC-07
        board = self.board()
        payload = {'board_id': board['id'], 'title': 'Desde chat', 'amount': '55.00'}
        response = self.client.post(self.url(self.conversation, 'opportunity/'), payload, format='json')
        self.assertEqual(response.status_code, 400)  # sin contacto vinculado
        customer = self.customer('Ana')
        self.put('contact/', {'customer_id': str(customer.id)})
        created = self.client.post(self.url(self.conversation, 'opportunity/'), payload, format='json')
        self.assertEqual(created.status_code, 201, created.content)
        body = created.json()
        self.assertEqual((body['opportunity']['title'], body['contact']['id']), ('Desde chat', str(customer.id)))


class AutoLinkTests(InboxBase):
    def test_links_single_active_customer_by_phone(self):  # AC-08, INV-07
        existing = self.customer('Ana Cliente', phone='+59176543210')
        self.customer('Inactiva', phone='+59176543210', active=False)
        self.receive('wamid.A')
        contact = self.client.get(self.url(self.conv())).json()['contact']
        self.assertEqual(contact, {'type': 'customer', 'id': str(existing.id), 'name': 'Ana Cliente'})

    def test_links_single_lead_when_no_customer_matches(self):  # AC-08
        lead = self.lead('Lia', phone='76543210', normalized='+' + ANA)
        self.receive('wamid.A')
        contact = self.client.get(self.url(self.conv())).json()['contact']
        self.assertEqual((contact['type'], contact['id']), ('lead', str(lead.id)))

    def test_ambiguous_or_foreign_matches_do_not_link(self):  # AC-08
        self.customer('Ana A', phone='+59176543210')
        self.customer('Ana B', phone='+59176543210')
        self.customer('Ajena', phone='+59171112222', company=make_company('Otra'))
        self.receive('wamid.A')
        self.receive('wamid.B', BETO)
        self.assertIsNone(self.client.get(self.url(self.conv())).json()['contact'])
        self.assertIsNone(self.client.get(self.url(self.conv(BETO))).json()['contact'])

    def test_manual_link_is_never_overwritten(self):  # INV-07
        manual = self.customer('Elegida', phone='+59170000009')
        self.receive('wamid.A')
        self.client.put(self.url(self.conv(), 'contact/'), {'customer_id': str(manual.id)}, format='json')
        self.customer('Coincide', phone='+59176543210')
        self.receive('wamid.B')
        self.assertEqual(self.client.get(self.url(self.conv())).json()['contact']['id'], str(manual.id))


class AccessAndIsolationTests(InboxBase):
    def test_requires_authentication(self):  # AC-10
        self.assertEqual(APIClient().get(INBOX).status_code, 401)

    def test_customers_module_disabled_blocks_the_inbox(self):  # AC-10
        for key in ('sales', 'reporting', 'customers'):
            self.client.post(f'/api/modules/{key}/disable/')
        self.assertEqual(self.client.get(INBOX).status_code, 403)

    def test_other_company_never_sees_or_changes_a_conversation(self):  # AC-10, INV-01
        self.receive('wamid.A')
        conversation = self.conv()
        _, other = self.other_company_client()
        self.assertEqual(other.get(INBOX).json()['count'], 0)
        for method, tail, data in (('get', '', None), ('get', 'messages/', None),
                                   ('post', 'messages/', {'type': 'text', 'body': 'x'}),
                                   ('put', 'owner/', {'owner_id': None}), ('put', 'contact/', {}),
                                   ('put', 'opportunity/', {'opportunity_id': None}),
                                   ('get', 'opportunities/', None)):
            response = getattr(other, method)(self.url(conversation, tail), data, format='json') if data is not None \
                else getattr(other, method)(self.url(conversation, tail))
            self.assertEqual(response.status_code, 404, (method, tail))

    def test_foreign_template_message_and_opportunity_are_404(self):  # AC-10, INV-01
        self.receive('wamid.A')
        self.receive('wamid.B', BETO)
        other_company, other = self.other_company_client()
        foreign_connection = self.connect(other_company, '222', verify='verify-2')
        foreign_template = TemplateModel.objects.create(
            company_id=other_company.id, connection=foreign_connection, name='ajena', language='es', category='UTILITY',
            status='APPROVED', synced_at=timezone.now())
        conversation = self.conv()
        response = self.client.post(self.url(conversation, 'messages/'),
                                    {'type': 'template', 'template_id': str(foreign_template.id)}, format='json')
        self.assertEqual(response.status_code, 404)
        self.client.post(self.url(conversation, 'messages/'), {'type': 'text', 'body': 'Hola'}, format='json')
        message_id = MessageModel.objects.get(direction='out').id
        beto = self.conv(BETO)  # el mensaje es de la conversación de Ana
        retry = self.client.post(self.url(beto, f'messages/{message_id}/retry/'))
        self.assertEqual(retry.status_code, 404)
        board = other.post(BOARDS, {'name': 'Otra'}, format='json').json()
        other.post(f"{BOARDS}{board['id']}/stages/", {'name': 'Nuevo'}, format='json')
        customer = self.customer('Otra', company=other_company)
        foreign_opportunity = other.post(OPPORTUNITIES, {'board_id': board['id'], 'title': 'X', 'amount': '1.00',
                                                         'customer_id': str(customer.id)}, format='json').json()
        link = self.client.put(self.url(conversation, 'opportunity/'), {'opportunity_id': foreign_opportunity['id']},
                               format='json')
        self.assertEqual(link.status_code, 404)

    def test_list_is_paginated(self):  # AC-01
        for n in range(3):
            self.receive(f'wamid.{n}', f'5917000000{n}')
        first = self.client.get(INBOX, {'page_size': 2}).json()
        self.assertEqual((first['count'], len(first['results']), bool(first['next'])), (3, 2, True))
        second = self.client.get(INBOX, {'page_size': 2, 'page': 2}).json()
        self.assertEqual((len(second['results']), second['next']), (1, None))
        self.assertEqual(len({r['id'] for r in first['results'] + second['results']}), 3)

    def test_assigning_does_not_overwrite_the_window_and_inbound_does_not_unassign(self):  # REV-04
        self.receive('wamid.A')
        conversation = self.conv()
        self.client.put(self.url(conversation, 'owner/'), {'owner_id': self.admin.id}, format='json')
        self.receive('wamid.B')  # el worker guarda `last_inbound_at` sin tocar el responsable
        self.assertEqual(self.client.get(self.url(conversation)).json()['owner']['id'], self.admin.id)
        before = ConversationModel.objects.get(id=conversation).last_inbound_at
        self.client.put(self.url(conversation, 'owner/'), {'owner_id': None}, format='json')
        self.assertEqual(ConversationModel.objects.get(id=conversation).last_inbound_at, before)
