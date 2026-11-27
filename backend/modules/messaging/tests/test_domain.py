"""Reglas puras: ventana de 24 h, teléfono, firma, backoff, estados y parser (AC-05, AC-06, AC-07, AC-09)."""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from django.test import SimpleTestCase

from modules.messaging.domain import webhook
from modules.messaging.domain.entities import Conversation, Message
from modules.messaging.domain.errors import MessagingValidationError, WindowClosed
from modules.messaging.domain.rules import (
    MAX_ATTEMPTS,
    backoff_delay,
    clean_secret_ref,
    normalize_phone,
    valid_signature,
    window_open,
)

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)


def message(status='queued'):
    return Message(uuid4(), uuid4(), uuid4(), uuid4(), 'out', 'text', {'body': 'hola'}, status=status)


class WindowTests(SimpleTestCase):
    def test_exact_24_hours_is_still_open(self):
        self.assertTrue(window_open(NOW - timedelta(hours=24), NOW))

    def test_one_second_past_24_hours_is_closed(self):
        self.assertFalse(window_open(NOW - timedelta(hours=24, seconds=1), NOW))

    def test_no_inbound_means_closed(self):
        self.assertFalse(window_open(None, NOW))
        conversation = Conversation(uuid4(), uuid4(), uuid4(), '59176543210')
        with self.assertRaises(WindowClosed):
            conversation.ensure_free_text_allowed(NOW)

    def test_inbound_never_moves_backwards(self):
        conversation = Conversation(uuid4(), uuid4(), uuid4(), '59176543210', NOW)
        conversation.register_inbound(NOW - timedelta(hours=1))
        self.assertEqual(conversation.last_inbound_at, NOW)


class PhoneTests(SimpleTestCase):
    def test_local_number_gets_country_code(self):
        self.assertEqual(normalize_phone('7654-3210', '591'), '59176543210')

    def test_international_forms(self):
        self.assertEqual(normalize_phone('+591 76543210', '591'), '59176543210')
        self.assertEqual(normalize_phone('0059176543210', '591'), '59176543210')
        self.assertEqual(normalize_phone('59176543210', '591'), '59176543210')

    def test_invalid(self):
        for raw in ('', 'abc', '123'):
            with self.assertRaises(MessagingValidationError):
                normalize_phone(raw, '591')


class SignatureTests(SimpleTestCase):
    def sign(self, body, secret):
        return 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    def test_valid_and_tampered(self):
        body = b'{"a":1}'
        self.assertTrue(valid_signature(body, self.sign(body, 's3cret'), 's3cret'))
        self.assertFalse(valid_signature(b'{"a":2}', self.sign(body, 's3cret'), 's3cret'))
        self.assertFalse(valid_signature(body, self.sign(body, 'otro'), 's3cret'))

    def test_missing_or_malformed(self):
        self.assertFalse(valid_signature(b'x', None, 's'))
        self.assertFalse(valid_signature(b'x', 'abc', 's'))
        self.assertFalse(valid_signature(b'x', 'sha256=zz', ''))


class BackoffAndSecretRefTests(SimpleTestCase):
    def test_exponential(self):
        self.assertEqual([backoff_delay(n) for n in (1, 2, 3)],
                         [timedelta(minutes=1), timedelta(minutes=2), timedelta(minutes=4)])

    def test_secret_ref_only_whatsapp_prefix(self):
        self.assertEqual(clean_secret_ref('WHATSAPP_TOKEN_A', 'secret_ref'), 'WHATSAPP_TOKEN_A')
        for bad in ('SECRET_KEY', 'DATABASE_URL', 'whatsapp_x', '', 'WHATSAPP_a b'):
            with self.assertRaises(MessagingValidationError):
                clean_secret_ref(bad, 'secret_ref')


class MessageStateTests(SimpleTestCase):
    def test_read_before_delivered_does_not_go_back(self):
        m = message('sent')
        self.assertTrue(m.advance('read'))
        self.assertFalse(m.advance('delivered'))
        self.assertFalse(m.advance('sent'))
        self.assertEqual(m.status, 'read')

    def test_failed_does_not_override_delivered(self):
        m = message('delivered')
        self.assertFalse(m.advance('failed'))
        self.assertEqual(m.status, 'delivered')

    def test_failed_from_sent_and_unknown_status_ignored(self):
        m = message('sent')
        self.assertTrue(m.advance('failed'))
        self.assertFalse(message('sent').advance('weird'))

    def test_retry_then_exhausted_fails_with_reason(self):
        m = message()
        for _ in range(MAX_ATTEMPTS - 1):
            self.assertTrue(m.schedule_retry(NOW, '503'))
        self.assertEqual(m.status, 'queued')
        self.assertFalse(m.schedule_retry(NOW, '503 final'))
        self.assertEqual((m.status, m.failure_reason), ('failed', '503 final'))


class ParserTests(SimpleTestCase):
    PAYLOAD = {'entry': [{'changes': [{'value': {
        'metadata': {'phone_number_id': '111'},
        'messages': [{'id': 'wamid.A', 'from': '59176543210', 'timestamp': '1790000000', 'type': 'text',
                      'text': {'body': 'hola'}}, {'id': 'wamid.B', 'from': '59176543210', 'type': 'image'}],
        'statuses': [{'id': 'wamid.C', 'status': 'delivered', 'timestamp': '1790000001',
                      'pricing': {'billable': True, 'pricing_model': 'PMP', 'category': 'utility'}}]}}]}]}

    def test_extracts_messages_statuses_and_pricing(self):
        inbound, statuses = webhook.parse(self.PAYLOAD, '111')
        self.assertEqual([i.wamid for i in inbound], ['wamid.A', 'wamid.B'])
        self.assertEqual(inbound[0].content, {'body': 'hola'})
        self.assertEqual((statuses[0].pricing_category, statuses[0].billable, statuses[0].pricing_model),
                         ('utility', True, 'PMP'))

    def test_other_number_and_garbage_are_ignored(self):
        self.assertEqual(webhook.parse(self.PAYLOAD, '999'), ([], []))
        for junk in (None, [], {'entry': 'x'}, {'entry': [{'changes': [1]}]}):
            self.assertEqual(webhook.phone_number_ids(junk), set())
