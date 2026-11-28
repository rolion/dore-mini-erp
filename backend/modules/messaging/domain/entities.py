"""Entidades de la mensajería. Los estados cambian por métodos, nunca por asignación directa."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from .errors import ConnectionNotActive, MessagingValidationError, NotRetryable, TemplateNotApproved, WindowClosed
from .rules import MAX_ATTEMPTS, backoff_delay, window_open

QUEUED, SENT, DELIVERED, READ, FAILED = 'queued', 'sent', 'delivered', 'read', 'failed'
STATUS_RANK = {QUEUED: 0, SENT: 1, DELIVERED: 2, READ: 3}
INBOUND, OUTBOUND = 'in', 'out'


@dataclass
class Connection:
    id: UUID
    company_id: UUID
    waba_id: str
    phone_number_id: str
    display_phone: str
    secret_ref: str
    app_secret_ref: str
    verify_token: str
    status: str = 'pending'
    status_reason: str = ''

    def ensure_usable(self) -> None:
        if self.status in ('disabled', 'error', 'pending'):
            raise ConnectionNotActive(self.status_reason or self.status)

    def mark_error(self, reason: str) -> None:
        self.status, self.status_reason = 'error', reason

    def mark_active(self) -> None:
        self.status, self.status_reason = 'active', ''


@dataclass
class Template:
    id: UUID
    name: str
    language: str
    category: str
    status: str
    components: list = field(default_factory=list)
    synced_at: datetime | None = None

    def ensure_sendable(self) -> None:
        if self.status != 'APPROVED':
            raise TemplateNotApproved(self.name)


@dataclass
class Conversation:
    id: UUID
    company_id: UUID
    connection_id: UUID
    phone: str
    last_inbound_at: datetime | None = None
    owner_id: int | None = None
    customer_id: UUID | None = None
    lead_id: UUID | None = None
    opportunity_id: UUID | None = None

    def assign(self, owner_id: int | None) -> None:
        self.owner_id = owner_id

    def link_contact(self, customer_id: UUID | None = None, lead_id: UUID | None = None) -> None:
        """A lo sumo un contacto: cliente o prospecto (INV-03). Sin ninguno, lo quita."""
        if customer_id is not None and lead_id is not None:
            raise MessagingValidationError({'customer_id': ['Vincula un cliente o un prospecto, no ambos.']})
        self.customer_id, self.lead_id = customer_id, lead_id

    def link_opportunity(self, opportunity_id: UUID | None) -> None:
        self.opportunity_id = opportunity_id

    def register_inbound(self, at: datetime) -> None:
        if self.last_inbound_at is None or at > self.last_inbound_at:
            self.last_inbound_at = at

    def window_is_open(self, now: datetime) -> bool:
        return window_open(self.last_inbound_at, now)

    def ensure_free_text_allowed(self, now: datetime) -> None:
        if not self.window_is_open(now):
            raise WindowClosed(self.phone)


@dataclass
class Message:
    id: UUID
    company_id: UUID
    connection_id: UUID
    conversation_id: UUID
    direction: str
    type: str
    content: dict[str, Any]
    status: str = QUEUED
    provider_message_id: str | None = None
    template_id: UUID | None = None
    pricing_category: str = ''
    billable: bool | None = None
    pricing_model: str = ''
    cost: Decimal | None = None
    currency: str = ''
    sent_at: datetime | None = None
    attempts: int = 0
    next_attempt_at: datetime | None = None
    failure_reason: str = ''
    created_at: datetime | None = None

    def mark_sent(self, provider_message_id: str, now: datetime) -> None:
        self.provider_message_id = provider_message_id
        self.sent_at, self.next_attempt_at, self.failure_reason = now, None, ''
        self.advance(SENT)

    def advance(self, new_status: str) -> bool:
        """Aplica un estado informado por Meta sin retroceder. `failed` no pisa delivered/read."""
        if new_status == FAILED:
            if self.status in (DELIVERED, READ, FAILED):
                return False
            self.status = FAILED
            return True
        new_rank = STATUS_RANK.get(new_status)
        current_rank = STATUS_RANK.get(self.status)
        if new_rank is None or (current_rank is not None and new_rank <= current_rank):
            return False
        self.status = new_status  # incluso desde `failed`: Meta puede confirmar la entrega más tarde
        if new_status != FAILED:
            self.failure_reason = ''
        return True

    def requeue(self) -> None:
        """Reintento manual (INV-08): solo un saliente `failed` vuelve a la cola, con intentos en cero."""
        if self.direction != OUTBOUND or self.status != FAILED:
            raise NotRetryable(self.status)
        self.status, self.attempts, self.next_attempt_at, self.failure_reason = QUEUED, 0, None, ''

    def record_pricing(self, category: str, billable: bool | None, model: str) -> None:
        self.pricing_category = category or self.pricing_category
        self.billable = billable if billable is not None else self.billable
        self.pricing_model = model or self.pricing_model

    def fail(self, reason: str) -> None:
        self.status, self.failure_reason, self.next_attempt_at = FAILED, reason[:500], None

    def schedule_retry(self, now: datetime, reason: str) -> bool:
        """Cuenta el intento fallido; devuelve True si se reprogramó y False si se agotaron (queda `failed`)."""
        self.attempts += 1
        if self.attempts >= MAX_ATTEMPTS:
            self.fail(reason)
            return False
        self.failure_reason = reason[:500]
        self.next_attempt_at = now + backoff_delay(self.attempts)
        return True
