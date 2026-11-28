"""Fachada pública de `messaging` para otros contextos (CRM: bandeja). `company_id` es siempre el primer argumento;
quien llama no importa modelos ni infraestructura de este módulo (ADR-crm-bandeja-whatsapp-business)."""
from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from .domain.entities import Conversation, Message
from .domain.errors import (  # noqa: F401  (reexportados: la fachada es el único punto de entrada de otros contextos)
    ConnectionNotActive,
    MessagingNotFound,
    MessagingValidationError,
    NotRetryable,
    TemplateNotApproved,
    WindowClosed,
)
from .domain.rules import WINDOW
from .infrastructure.django.repositories import (
    DjangoConnectionRepository,
    DjangoConversationRepository,
    DjangoMessageRepository,
)
from .infrastructure.factory import SystemClock, send_service

THREAD_LIMIT = 200


@dataclass(frozen=True)
class ConversationSummary:
    conversation: Conversation
    last_message: Message | None
    window_open: bool
    window_expires_at: datetime | None


def _summary(conversation: Conversation, last: Message | None, now: datetime) -> ConversationSummary:
    expires = conversation.last_inbound_at + WINDOW if conversation.last_inbound_at else None
    return ConversationSummary(conversation, last, conversation.window_is_open(now), expires)


def _conversation(company_id: UUID, conversation_id: UUID) -> Conversation:
    found = DjangoConversationRepository(company_id).find(conversation_id)
    if found is None:
        raise MessagingNotFound('conversation')
    return found


def list_conversations(company_id: UUID, *, owner_id: int | None = None, unassigned: bool = False,
                       opportunity_id: UUID | None = None, search: str | None = None,
                       customer_ids: Collection[UUID] = (), lead_ids: Collection[UUID] = (),
                       offset: int = 0, limit: int = 25) -> tuple[int, list[ConversationSummary]]:
    """Página de conversaciones por último mensaje. `search` coincide por teléfono o por los contactos dados."""
    total, conversations, last = DjangoConversationRepository(company_id).page(
        owner_id=owner_id, unassigned=unassigned, opportunity_id=opportunity_id, search=search,
        customer_ids=customer_ids, lead_ids=lead_ids, offset=offset, limit=limit)
    now = SystemClock().now()
    return total, [_summary(c, last.get(c.id), now) for c in conversations]


def get_conversation(company_id: UUID, conversation_id: UUID) -> ConversationSummary:
    conversation = _conversation(company_id, conversation_id)
    return _summary(conversation, DjangoConversationRepository(company_id).last_message(conversation_id),
                    SystemClock().now())


def list_messages(company_id: UUID, conversation_id: UUID, after: datetime | None = None) -> list[Message]:
    _conversation(company_id, conversation_id)
    return DjangoMessageRepository(company_id).thread(conversation_id, after, THREAD_LIMIT)


def connection_active(company_id: UUID) -> bool:
    connection = DjangoConnectionRepository(company_id).get()
    return connection is not None and connection.status == 'active'


def send_text(company_id: UUID, conversation_id: UUID, body: str) -> Message:
    return send_service(company_id).text(_conversation(company_id, conversation_id).phone, body)


def send_template(company_id: UUID, conversation_id: UUID, template_id: UUID, components: list | None = None
                  ) -> Message:
    return send_service(company_id).template(_conversation(company_id, conversation_id).phone, template_id,
                                             components)


def retry_message(company_id: UUID, conversation_id: UUID, message_id: UUID) -> Message:
    """Reencola un saliente `failed` (INV-08); el worker lo entrega. Texto con la ventana cerrada → `WindowClosed`."""
    conversation = _conversation(company_id, conversation_id)
    messages = DjangoMessageRepository(company_id)
    message = messages.get(message_id)
    if message is None or message.conversation_id != conversation_id:
        raise MessagingNotFound('message')
    message.requeue()
    if message.type != 'template':
        conversation.ensure_free_text_allowed(SystemClock().now())
    messages.save(message)
    return message


def assign(company_id: UUID, conversation_id: UUID, owner_id: int | None) -> Conversation:
    repository = DjangoConversationRepository(company_id)
    conversation = _conversation(company_id, conversation_id)
    conversation.assign(owner_id)
    repository.save(conversation)
    return conversation


def link_contact(company_id: UUID, conversation_id: UUID, customer_id: UUID | None = None,
                 lead_id: UUID | None = None, opportunity_id: UUID | None = None) -> Conversation:
    """Fija el contacto y la oportunidad de la conversación; las reglas de coherencia las valida CRM."""
    repository = DjangoConversationRepository(company_id)
    conversation = _conversation(company_id, conversation_id)
    conversation.link_contact(customer_id, lead_id)
    conversation.link_opportunity(opportunity_id)
    repository.save(conversation)
    return conversation


def link_opportunity(company_id: UUID, conversation_id: UUID, opportunity_id: UUID | None) -> Conversation:
    repository = DjangoConversationRepository(company_id)
    conversation = _conversation(company_id, conversation_id)
    conversation.link_opportunity(opportunity_id)
    repository.save(conversation)
    return conversation


def subscribe_inbound(handler: Callable[[UUID, UUID], None]) -> None:
    """Avisa `handler(company_id, conversation_id)` por cada mensaje entrante nuevo (en el proceso que lo guarda:
    servidor web o worker, así que quien se suscribe debe hacerlo al arrancar la app)."""
    from .application.events import subscribe
    subscribe(lambda event: handler(event.company_id, event.conversation_id))
