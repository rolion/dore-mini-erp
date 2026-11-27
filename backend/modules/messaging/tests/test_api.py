"""Webhook, worker, envío, reintentos y API de conexión con PostgreSQL (AC-01…AC-11)."""
import hashlib
import hmac
import io
import json
import os
import urllib.error
from datetime import timedelta
from unittest import mock

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.messaging.application import events
from modules.messaging.domain.errors import PermanentGatewayError, TransientGatewayError
from modules.messaging.domain.rules import secret_ref_prefix
from modules.messaging.infrastructure.django.models import (
    ConnectionModel,
    ConversationModel,
    MessageModel,
    TemplateModel,
    WebhookEventModel,
)
from modules.messaging.infrastructure.fake_gateway import FakeMessagingGateway
from modules.messaging.infrastructure.whatsapp_adapter import WhatsAppCloudAdapter
from modules.messaging.infrastructure.worker import deliver_next_message, process_all, process_next_event

WEBHOOK = '/api/messaging/whatsapp/webhook/'
CONNECTION = '/api/messaging/whatsapp/connection/'
APP_SECRET = 'app-secret-value-123'
TOKEN = 'EAAG-super-secret-token'


def signed(body: dict | bytes, secret: str = APP_SECRET):
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    return raw, 'sha256=' + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def inbound_payload(phone_number_id='111', wamid='wamid.IN1', sender='59176543210', ts=None):
    ts = ts or int(timezone.now().timestamp())
    return {'object': 'whatsapp_business_account', 'entry': [{'id': '9', 'changes': [{'field': 'messages', 'value': {
        'messaging_product': 'whatsapp', 'metadata': {'phone_number_id': phone_number_id},
        'messages': [{'id': wamid, 'from': sender, 'timestamp': str(ts), 'type': 'text',
                      'text': {'body': 'hola'}}]}}]}]}


def status_payload(wamid, status, phone_number_id='111', pricing=None, errors=None):
    item = {'id': wamid, 'status': status, 'timestamp': str(int(timezone.now().timestamp())),
            'recipient_id': '59176543210'}
    if pricing:
        item['pricing'] = pricing
    if errors:
        item['errors'] = errors
    return {'entry': [{'changes': [{'field': 'messages', 'value': {
        'metadata': {'phone_number_id': phone_number_id}, 'statuses': [item]}}]}]}


class MessagingBase(APITestCase):
    def setUp(self):
        FakeMessagingGateway.reset()
        self.company = make_company('Empresa Uno')
        prefix = secret_ref_prefix(self.company.id)
        self.token_ref, self.app_ref = f'{prefix}TOKEN', f'{prefix}APP_SECRET'
        env = mock.patch.dict(os.environ, {self.app_ref: APP_SECRET, self.token_ref: TOKEN})
        env.start()
        self.addCleanup(env.stop)
        self.admin = make_admin(self.company, 'ana')
        self.client = APIClient()
        authenticate(self.client, self.admin)
        self.connection = self.connect(self.company, '111')

    def connect(self, company, phone_number_id, verify='verify-1'):
        return ConnectionModel.objects.create(
            company_id=company.id, waba_id='9', phone_number_id=phone_number_id, secret_ref=self.token_ref,
            app_secret_ref=self.app_ref, verify_token=verify, status='active')

    def post_webhook(self, payload, secret=APP_SECRET, header=None):
        raw, signature = signed(payload, secret)
        extra = {} if header is False else {'HTTP_X_HUB_SIGNATURE_256': header or signature}
        return APIClient().post(WEBHOOK, raw, content_type='application/json', **extra)

    def template(self, status='APPROVED'):
        return TemplateModel.objects.create(company_id=self.company.id, connection=self.connection, name='hello_world',
                                            language='en_US', category='UTILITY', status=status,
                                            synced_at=timezone.now())

    def conversation(self, last_inbound_at=None, phone='59176543210'):
        return ConversationModel.objects.create(company_id=self.company.id, connection=self.connection, phone=phone,
                                                last_inbound_at=last_inbound_at)


class WebhookVerificationTests(MessagingBase):
    def test_get_returns_challenge_only_with_the_right_token(self):  # AC-01
        ok = APIClient().get(WEBHOOK, {'hub.mode': 'subscribe', 'hub.verify_token': 'verify-1',
                                       'hub.challenge': '12345'})
        self.assertEqual((ok.status_code, ok.content), (200, b'12345'))
        bad = APIClient().get(WEBHOOK, {'hub.mode': 'subscribe', 'hub.verify_token': 'otro', 'hub.challenge': '12345'})
        self.assertEqual(bad.status_code, 403)
        self.assertEqual(APIClient().get(WEBHOOK, {'hub.mode': 'subscribe', 'hub.challenge': '1'}).status_code, 403)

    def test_invalid_signature_is_401_and_persists_nothing(self):  # AC-02
        payload = inbound_payload()
        for response in (self.post_webhook(payload, secret='otro'), self.post_webhook(payload, header=False),
                         self.post_webhook(payload, header='sha256=00')):
            self.assertEqual(response.status_code, 401)
        self.assertEqual(WebhookEventModel.objects.count(), 0)
        self.assertEqual(MessageModel.objects.count(), 0)

    def test_unknown_number_is_401(self):
        self.assertEqual(self.post_webhook(inbound_payload('999')).status_code, 401)
        self.assertEqual(WebhookEventModel.objects.count(), 0)

    def test_oversized_body_is_413(self):
        raw = b'{"x":"' + b'a' * 1_100_000 + b'"}'
        self.assertEqual(APIClient().post(WEBHOOK, raw, content_type='application/json').status_code, 413)

    def test_valid_post_only_enqueues_and_answers_200(self):  # AC-03
        with mock.patch('modules.messaging.infrastructure.worker.event_processor') as processor:
            response = self.post_webhook(inbound_payload())
        self.assertEqual(response.status_code, 200)
        processor.assert_not_called()
        self.assertEqual(MessageModel.objects.count(), 0)
        event = WebhookEventModel.objects.get()
        self.assertEqual((event.status, event.company_id), ('pending', self.company.id))

    def test_missing_app_secret_variable_is_503_so_meta_retries(self):
        with mock.patch.dict(os.environ, {self.app_ref: ''}):
            self.assertEqual(self.post_webhook(inbound_payload()).status_code, 503)
        self.assertEqual(WebhookEventModel.objects.count(), 0)


class InboundProcessingTests(MessagingBase):
    def test_repeated_wamid_creates_one_message_and_one_event(self):  # AC-04, AC-10
        seen = []
        events.subscribe(seen.append)
        self.addCleanup(events.unsubscribe, seen.append)
        for _ in range(2):
            self.assertEqual(self.post_webhook(inbound_payload()).status_code, 200)
        self.assertEqual(process_all(), 2)
        message = MessageModel.objects.get()
        self.assertEqual((message.direction, message.content, message.company_id),
                         ('in', {'body': 'hola'}, self.company.id))
        self.assertEqual(len(seen), 1)
        event = seen[0]
        self.assertEqual((event.company_id, event.message_id, event.phone),
                         (self.company.id, message.id, '59176543210'))
        self.assertEqual(set(WebhookEventModel.objects.values_list('status', flat=True)), {'done'})

    def test_inbound_sets_last_inbound_at_and_opens_the_window(self):
        self.post_webhook(inbound_payload())
        process_all()
        conversation = ConversationModel.objects.get()
        self.assertLess(timezone.now() - conversation.last_inbound_at, timedelta(minutes=1))

    def test_unknown_payload_is_done_without_effect(self):
        self.post_webhook({'entry': [{'changes': [{'value': {'metadata': {'phone_number_id': '111'},
                                                             'weird': True}}]}]})
        process_all()
        self.assertEqual(MessageModel.objects.count(), 0)
        self.assertEqual(WebhookEventModel.objects.get().status, 'done')

    def test_isolation_between_companies(self):
        other = make_company('Empresa Dos')
        self.connect(other, '222', verify='verify-2')
        self.post_webhook(inbound_payload('222', 'wamid.OTHER'))
        process_all()
        self.assertEqual(MessageModel.objects.get().company_id, other.id)
        self.assertEqual(MessageModel.objects.filter(company_id=self.company.id).count(), 0)


class StatusTests(MessagingBase):
    def sent_message(self, status='sent'):
        conversation = self.conversation()
        return MessageModel.objects.create(
            company_id=self.company.id, connection=self.connection, conversation=conversation, direction='out',
            type='text', content={'body': 'x'}, status=status, provider_message_id='wamid.OUT')

    def push(self, payload):
        self.post_webhook(payload)
        process_all()

    def test_out_of_order_status_does_not_go_back(self):  # AC-06
        self.sent_message()
        self.push(status_payload('wamid.OUT', 'read'))
        self.push(status_payload('wamid.OUT', 'delivered'))
        self.assertEqual(MessageModel.objects.get().status, 'read')

    def test_pricing_is_stored_and_cost_stays_null(self):  # AC-08
        self.sent_message()
        self.push(status_payload('wamid.OUT', 'delivered',
                                 pricing={'billable': True, 'pricing_model': 'PMP', 'category': 'utility'}))
        m = MessageModel.objects.get()
        self.assertEqual((m.status, m.pricing_category, m.billable, m.pricing_model, m.cost, m.currency),
                         ('delivered', 'utility', True, 'PMP', None, ''))

    def test_failed_records_reason_but_not_over_delivered(self):
        self.sent_message()
        self.push(status_payload('wamid.OUT', 'failed', errors=[{'code': 131026, 'title': 'Undeliverable'}]))
        m = MessageModel.objects.get()
        self.assertEqual((m.status, m.failure_reason), ('failed', '131026 Undeliverable'))

    def test_status_of_unknown_message_is_ignored(self):
        self.push(status_payload('wamid.NOPE', 'read'))
        self.assertEqual(WebhookEventModel.objects.get().status, 'done')


class SendTests(MessagingBase):
    def send_test(self, template, to='76543210'):
        return self.client.post('/api/messaging/whatsapp/test-message/', {'to': to, 'template_id': str(template.id)},
                                format='json')

    def test_template_message_is_queued_then_sent_by_the_worker(self):  # AC-11
        template = self.template()
        response = self.send_test(template)
        self.assertEqual((response.status_code, response.json()['status']), (202, 'queued'))
        self.assertTrue(deliver_next_message())
        m = MessageModel.objects.get()
        self.assertEqual((m.status, m.provider_message_id is not None), ('sent', True))
        self.assertEqual(FakeMessagingGateway.sent[0][:2], ('template', '59176543210'))

    def test_unapproved_template_is_409(self):
        response = self.send_test(self.template('REJECTED'))
        self.assertEqual((response.status_code, response.json()['code']), (409, 'template_not_approved'))

    def test_free_text_outside_window_fails_with_window_closed(self):  # AC-05
        from modules.messaging.domain.errors import WindowClosed
        from modules.messaging.infrastructure.factory import send_service
        self.conversation(last_inbound_at=timezone.now() - timedelta(hours=24, minutes=1))
        with self.assertRaises(WindowClosed):
            send_service(self.company.id).text('76543210', 'hola')
        self.assertEqual(MessageModel.objects.count(), 0)

    def test_free_text_inside_window_is_allowed(self):
        from modules.messaging.infrastructure.factory import send_service
        self.conversation(last_inbound_at=timezone.now() - timedelta(hours=23))
        send_service(self.company.id).text('76543210', 'hola')
        deliver_next_message()
        self.assertEqual(MessageModel.objects.get().status, 'sent')
        self.assertEqual(FakeMessagingGateway.sent[0][0], 'text')

    def test_transient_errors_retry_with_backoff_then_fail_with_reason(self):  # AC-07
        self.send_test(self.template())
        FakeMessagingGateway.failures = [TransientGatewayError('429 rate limit')] * 5
        for attempt in range(1, 5):
            self.assertTrue(deliver_next_message())
            m = MessageModel.objects.get()
            self.assertEqual((m.status, m.attempts), ('queued', attempt))
            self.assertGreater(m.next_attempt_at, timezone.now())
            MessageModel.objects.update(next_attempt_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(deliver_next_message())
        m = MessageModel.objects.get()
        self.assertEqual((m.status, m.attempts, m.failure_reason), ('failed', 5, '429 rate limit'))
        self.assertFalse(deliver_next_message())

    def test_not_retried_before_its_time(self):
        self.send_test(self.template())
        FakeMessagingGateway.failures = [TransientGatewayError('503')]
        deliver_next_message()
        self.assertFalse(deliver_next_message())

    def test_expired_token_fails_without_retry_and_marks_connection(self):
        template = self.template()
        self.send_test(template)
        FakeMessagingGateway.failures = [PermanentGatewayError('401 190 expired', provider_code=190,
                                                               token_expired=True)]
        deliver_next_message()
        m = MessageModel.objects.get()
        self.assertEqual((m.status, m.attempts), ('failed', 0))
        self.connection.refresh_from_db()
        self.assertEqual((self.connection.status, self.connection.status_reason), ('error', 'token_expired'))
        self.assertEqual(self.send_test(template).status_code, 409)


class AdapterTests(MessagingBase):
    def adapter(self, opener):
        return WhatsAppCloudAdapter(TOKEN, '111', '9', base_url='https://graph.test', api_version='v21.0',
                                    opener=opener)

    @staticmethod
    def http_error(status, body):
        return urllib.error.HTTPError('u', status, 'x', {}, io.BytesIO(json.dumps(body).encode()))

    def test_429_and_5xx_are_transient_and_4xx_permanent(self):
        for status in (429, 500, 503):
            with self.assertRaises(TransientGatewayError):
                self.adapter(mock.Mock(side_effect=self.http_error(status, {}))).send_text('1', 'x')
        with self.assertRaises(PermanentGatewayError) as ctx:
            self.adapter(mock.Mock(side_effect=self.http_error(401, {'error': {'code': 190, 'message': 'expired'}}))
                         ).send_text('1', 'x')
        self.assertTrue(ctx.exception.token_expired)

    def test_network_error_is_transient_and_error_text_has_no_token(self):
        with self.assertRaises(TransientGatewayError) as ctx:
            self.adapter(mock.Mock(side_effect=urllib.error.URLError('boom'))).send_text('1', 'x')
        self.assertNotIn(TOKEN, str(ctx.exception))

    def test_success_sends_bearer_and_returns_wamid(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"messages":[{"id":"wamid.OK"}]}'
        opener = mock.Mock(return_value=response)
        result = self.adapter(opener).send_template('591', 'hello_world', 'en_US', [])
        self.assertEqual(result.provider_message_id, 'wamid.OK')
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header('Authorization'), f'Bearer {TOKEN}')
        self.assertEqual(json.loads(request.data)['template']['language'], {'code': 'en_US'})


class ConnectionApiTests(MessagingBase):
    def setUp(self):
        super().setUp()
        ConnectionModel.objects.all().delete()
        self.BODY = {'waba_id': '9', 'phone_number_id': '555', 'display_phone': '+591 76543210',
                     'secret_ref': self.token_ref, 'app_secret_ref': self.app_ref}

    def test_save_activates_when_secrets_exist_and_never_returns_secret_values(self):  # AC-09, AC-11
        response = self.client.put(CONNECTION, self.BODY, format='json')
        data = response.json()
        self.assertEqual((response.status_code, data['status'], data['display_phone']), (200, 'active', '59176543210'))
        self.assertTrue(data['verify_token'])
        self.assertNotIn(TOKEN, response.content.decode())
        self.assertNotIn(APP_SECRET, response.content.decode())
        self.assertEqual(self.client.get(CONNECTION).json()['phone_number_id'], '555')

    def test_pending_when_variables_are_missing(self):
        with mock.patch.dict(os.environ, {self.token_ref: ''}):
            data = self.client.put(CONNECTION, self.BODY, format='json').json()
        self.assertEqual((data['status'], data['status_reason']), ('pending', 'secrets_missing'))

    def test_rejects_refs_that_could_leak_server_secrets(self):
        for ref in ('SECRET_KEY', 'DATABASE_URL', 'WHATSAPP_TOKEN'):
            response = self.client.put(CONNECTION, {**self.BODY, 'secret_ref': ref}, format='json')
            self.assertEqual(response.status_code, 400)

    def test_a_company_cannot_use_the_variables_of_another_company(self):  # REV-01
        other = make_company('Empresa Dos')
        foreign = f'{secret_ref_prefix(other.id)}TOKEN'
        with mock.patch.dict(os.environ, {foreign: 'ajeno'}):
            for field in ('secret_ref', 'app_secret_ref'):
                response = self.client.put(CONNECTION, {**self.BODY, field: foreign}, format='json')
                self.assertEqual(response.status_code, 400, field)
                self.assertIn(secret_ref_prefix(self.company.id), response.json()[field][0])
        self.assertEqual(ConnectionModel.objects.count(), 0)

    def test_get_exposes_the_required_prefix_even_without_a_connection(self):
        data = self.client.get(CONNECTION).json()
        self.assertEqual((data['configured'], data['secret_ref_prefix']), (False, secret_ref_prefix(self.company.id)))

    def test_number_of_another_company_is_rejected(self):
        self.connect(make_company('Otra'), '555', verify='v-x')
        self.assertEqual(self.client.put(CONNECTION, self.BODY, format='json').status_code, 400)

    def test_verify_token_is_stable_across_updates(self):
        first = self.client.put(CONNECTION, self.BODY, format='json').json()['verify_token']
        again = self.client.put(CONNECTION, {**self.BODY, 'waba_id': '10'}, format='json').json()['verify_token']
        self.assertEqual(first, again)

    def test_requires_admin_of_a_company_and_isolates_data(self):
        self.assertEqual(APIClient().get(CONNECTION).status_code, 401)
        other = make_admin(make_company('Otra Empresa'), 'beto')
        client = APIClient()
        authenticate(client, other)
        self.client.put(CONNECTION, self.BODY, format='json')
        self.assertFalse(client.get(CONNECTION).json()['configured'])
        self.assertEqual(client.get('/api/messaging/whatsapp/templates/').json()['results'], [])

    def test_template_sync_lists_templates_and_activates(self):
        self.client.put(CONNECTION, self.BODY, format='json')
        FakeMessagingGateway.templates = [
            {'name': 'promo', 'language': 'es', 'category': 'MARKETING', 'status': 'PAUSED', 'components': []}]
        rows = self.client.post('/api/messaging/whatsapp/templates/sync/').json()['results']
        self.assertEqual([(r['name'], r['status']) for r in rows], [('promo', 'PAUSED')])
        self.assertEqual(self.client.get('/api/messaging/whatsapp/templates/').json()['results'][0]['name'], 'promo')

    def test_sync_without_connection_is_404(self):
        self.assertEqual(self.client.post('/api/messaging/whatsapp/templates/sync/').status_code, 404)


class DisabledConnectionTests(MessagingBase):
    def test_signed_event_of_a_disabled_connection_is_accepted_without_effect(self):  # REV-02
        ConnectionModel.objects.update(status='disabled')
        self.assertEqual(self.post_webhook(inbound_payload()).status_code, 200)
        self.assertEqual(WebhookEventModel.objects.count(), 0)
        self.assertEqual(self.post_webhook(inbound_payload(), secret='otro').status_code, 401)


class AtomicProcessingTests(MessagingBase):
    def test_a_partial_failure_rolls_everything_back_and_publishes_nothing(self):  # REV-03
        seen = []
        events.subscribe(seen.append)
        self.addCleanup(events.unsubscribe, seen.append)
        self.post_webhook(inbound_payload())
        target = 'modules.messaging.infrastructure.django.repositories.DjangoConversationRepository.save'
        with mock.patch(target, side_effect=RuntimeError('boom')):
            process_next_event()
        self.assertEqual(MessageModel.objects.count(), 0)
        self.assertEqual(seen, [])
        self.assertEqual(WebhookEventModel.objects.get().status, 'failed')

    def test_the_event_is_published_after_the_message_is_committed(self):
        found = []
        handler = lambda event: found.append(MessageModel.objects.filter(id=event.message_id).exists())  # noqa: E731
        events.subscribe(handler)
        self.addCleanup(events.unsubscribe, handler)
        self.post_webhook(inbound_payload())
        process_all()
        self.assertEqual(found, [True])


@override_settings(MESSAGING_PROVIDER='fake')
class NoSecretsInLogsTests(MessagingBase):
    def test_processing_failure_logs_do_not_contain_secret_values(self):
        self.post_webhook(inbound_payload())
        with self.assertLogs('modules.messaging', level='INFO') as logs, \
                mock.patch('modules.messaging.infrastructure.worker.event_processor', side_effect=RuntimeError('x')):
            process_next_event()
        text = '\n'.join(logs.output)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn(APP_SECRET, text)
