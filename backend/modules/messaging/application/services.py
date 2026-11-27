"""Casos de uso de la mensajería: recibir webhook, procesarlo, enviar y sincronizar plantillas."""
import logging
import secrets as token_generator
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from ..domain import webhook
from ..domain.entities import INBOUND, OUTBOUND, Connection, Message
from ..domain.errors import (
    ConnectionNotActive,
    InvalidSignature,
    MessagingNotFound,
    MessagingValidationError,
    PayloadTooLarge,
    PermanentGatewayError,
    SecretUnavailable,
    TransientGatewayError,
)
from ..domain.events import InboundMessageReceived
from ..domain.rules import clean_secret_ref, normalize_phone, secret_ref_prefix, valid_signature

logger = logging.getLogger(__name__)
MAX_BODY_BYTES = 1_000_000


@dataclass
class ConnectionInput:
    waba_id: str
    phone_number_id: str
    display_phone: str
    secret_ref: str
    app_secret_ref: str


def _digits(value: str, field: str) -> str:
    text = (value or '').strip()
    if not text.isdigit() or len(text) > 40:
        raise MessagingValidationError({field: ['Usa solo números.']})
    return text


class ConnectionService:
    def __init__(self, company_id: UUID, connections, secrets, default_country_code: str):
        self.company_id, self.connections, self.secrets = company_id, connections, secrets
        self.cc = default_country_code

    def get(self) -> Connection | None:
        return self.connections.get()

    def save(self, data: ConnectionInput) -> Connection:
        waba, number = _digits(data.waba_id, 'waba_id'), _digits(data.phone_number_id, 'phone_number_id')
        prefix = secret_ref_prefix(self.company_id)
        refs = (clean_secret_ref(data.secret_ref, 'secret_ref', prefix),
                clean_secret_ref(data.app_secret_ref, 'app_secret_ref', prefix))
        if self.connections.phone_number_taken(number):
            raise MessagingValidationError({'phone_number_id': ['Este número ya está conectado a otra empresa.']})
        phone = normalize_phone(data.display_phone, self.cc) if (data.display_phone or '').strip() else ''
        current = self.connections.get()
        connection = Connection(
            current.id if current else uuid4(), self.company_id, waba, number, phone, refs[0], refs[1],
            current.verify_token if current else token_generator.token_urlsafe(24))
        if self.secrets.available(refs[0], self.company_id) and self.secrets.available(refs[1], self.company_id):
            connection.mark_active()
        else:
            connection.status, connection.status_reason = 'pending', 'secrets_missing'
        return self.connections.save(connection)


class ReceiveWebhook:
    """Valida la firma y guarda el cuerpo en la cola. No procesa nada: el webhook debe responder en < 2 s."""

    def __init__(self, directory, queue, secrets, parse_json):
        self.directory, self.queue, self.secrets, self.parse_json = directory, queue, secrets, parse_json

    def handle(self, body: bytes, signature: str | None) -> int:
        if len(body) > MAX_BODY_BYTES:
            raise PayloadTooLarge()
        payload = self.parse_json(body)
        numbers = webhook.phone_number_ids(payload)
        if not numbers:
            raise InvalidSignature()
        connections = []
        for number in numbers:  # todos los números del cuerpo deben verificar con su propio App Secret
            connection = self.directory.by_phone_number_id(number)
            if connection is None:
                raise InvalidSignature()
            if not valid_signature(body, signature, self.secrets.get(connection.app_secret_ref, connection.company_id)):
                raise InvalidSignature()
            connections.append(connection)
        accepted = [c for c in connections if c.status != 'disabled']  # firmado y válido, pero sin efecto (REV-02)
        for connection in accepted:
            self.queue.add(connection, payload)
        return len(accepted)


class ProcessWebhookEvent:
    """Caso de uso del worker (`process_webhook_event`): aplica mensajes y estados de un evento ya verificado."""

    def __init__(self, connection: Connection, messages, conversations, clock, default_country_code: str):
        self.connection, self.messages, self.conversations = connection, messages, conversations
        self.clock, self.cc = clock, default_country_code

    def run(self, payload) -> list[InboundMessageReceived]:
        """Aplica el payload y devuelve los eventos de dominio: quien llama los publica DESPUÉS de confirmar la
        transacción, para que un fallo a medias no deje un evento sin su mensaje (REV-03). La publicación es en
        memoria y «a lo sumo una vez»: si el proceso cae justo tras el commit, el evento no se reemite (REV-05)."""
        inbound, statuses = webhook.parse(payload, self.connection.phone_number_id)
        published = [event for item in inbound if (event := self._inbound(item)) is not None]
        for item in statuses:
            self._status(item)
        return published

    def _inbound(self, item) -> InboundMessageReceived | None:
        conversation = self.conversations.get_or_create(self.connection.id,
                                                        normalize_phone('+' + item.sender, self.cc))
        message = Message(uuid4(), self.connection.company_id, self.connection.id, conversation.id, INBOUND,
                          item.type, item.content, status='delivered', provider_message_id=item.wamid,
                          sent_at=item.at)
        stored, created = self.messages.add_inbound_once(message)
        if not created:
            return None  # mismo wamid repetido: un solo Message y un solo evento
        conversation.register_inbound(item.at)
        self.conversations.save(conversation)
        return InboundMessageReceived(self.connection.company_id, self.connection.id, conversation.id,
                                      stored.id, conversation.phone, item.type, item.at)

    def _status(self, item) -> None:
        message = self.messages.by_provider_id(self.connection.id, item.wamid)
        if message is None or message.direction != OUTBOUND:
            logger.info('Estado de un mensaje desconocido (%s); se ignora', item.status)
            return
        message.record_pricing(item.pricing_category, item.billable, item.pricing_model)
        if message.advance(item.status) and item.status == 'failed':
            message.failure_reason = (item.error or 'failed')[:500]
        self.messages.save(message)


class SendMessages:
    """Encola envíos (valida ventana/plantilla al instante) y los entrega con reintentos."""

    def __init__(self, company_id: UUID, connections, conversations, messages, templates, clock,
                 default_country_code: str):
        self.company_id, self.connections, self.conversations = company_id, connections, conversations
        self.messages, self.templates, self.clock, self.cc = messages, templates, clock, default_country_code

    def _connection(self) -> Connection:
        connection = self.connections.get()
        if connection is None:
            raise MessagingNotFound('connection')
        connection.ensure_usable()
        return connection

    def _queue(self, connection, phone, kind, content, template_id=None) -> Message:
        conversation = self.conversations.get_or_create(connection.id, phone)
        return conversation, Message(uuid4(), self.company_id, connection.id, conversation.id, OUTBOUND, kind,
                                     content, template_id=template_id)

    def text(self, to: str, body: str) -> Message:
        connection = self._connection()
        if not (body or '').strip():
            raise MessagingValidationError({'body': ['El mensaje no puede estar vacío.']})
        conversation, message = self._queue(connection, normalize_phone(to, self.cc), 'text', {'body': body.strip()})
        conversation.ensure_free_text_allowed(self.clock.now())
        return self.messages.add(message)

    def interactive(self, to: str, interactive: dict) -> Message:
        connection = self._connection()
        conversation, message = self._queue(connection, normalize_phone(to, self.cc), 'interactive', interactive)
        conversation.ensure_free_text_allowed(self.clock.now())
        return self.messages.add(message)

    def template(self, to: str, template_id: UUID, components: list | None = None) -> Message:
        connection = self._connection()
        template = self.templates.get(template_id)
        if template is None:
            raise MessagingNotFound('template')
        template.ensure_sendable()
        _, message = self._queue(connection, normalize_phone(to, self.cc), 'template',
                                 {'name': template.name, 'language': template.language,
                                  'components': components or []}, template.id)
        return self.messages.add(message)

    def deliver(self, message_id: UUID, gateway_for) -> None:
        """Entrega un mensaje en cola. 429/5xx → backoff; agotados o 4xx → `failed` con el motivo."""
        message = self.messages.get(message_id)
        if message is None or message.status != 'queued':
            return
        connection = self.connections.get()
        now = self.clock.now()
        try:
            if connection is None:
                raise PermanentGatewayError('connection_missing')
            connection.ensure_usable()
            conversation = self.conversations.get(message.conversation_id)
            gateway = gateway_for(connection)
            if message.type == 'template':
                c = message.content
                result = gateway.send_template(conversation.phone, c['name'], c['language'], c.get('components', []))
            else:
                conversation.ensure_free_text_allowed(now)  # la ventana pudo cerrarse mientras esperaba
                if message.type == 'text':
                    result = gateway.send_text(conversation.phone, message.content['body'])
                else:
                    result = gateway.send_interactive(conversation.phone, message.content)
            message.mark_sent(result.provider_message_id, now)
        except TransientGatewayError as exc:
            message.schedule_retry(now, str(exc) or 'provider_unavailable')
        except PermanentGatewayError as exc:
            message.fail(exc.reason)
            if exc.token_expired and connection is not None:
                connection.mark_error('token_expired')
                self.connections.save(connection)
        except (SecretUnavailable, ConnectionNotActive) as exc:
            message.fail(f'{exc.code}')
        except Exception as exc:  # incluye WindowClosed
            message.fail(getattr(exc, 'code', 'error'))
            logger.exception('Falló la entrega del mensaje %s', message.id)
        self.messages.save(message)

    def sync_templates(self, gateway_for, now: datetime) -> list:
        connection = self._connection()
        try:
            rows = gateway_for(connection).list_templates()
        except PermanentGatewayError as exc:
            if exc.token_expired:
                connection.mark_error('token_expired')
                self.connections.save(connection)
            raise
        if connection.status != 'active':
            connection.mark_active()
            self.connections.save(connection)
        return self.templates.replace_all(connection.id, rows, now)
