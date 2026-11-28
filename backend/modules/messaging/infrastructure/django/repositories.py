"""Repositorios Django. Los scoped por empresa reciben `company_id`; `ConnectionDirectory`, `EventQueue` y
`OutboxQueue` son transversales a propósito (webhook y worker no tienen usuario: la empresa sale de la conexión)."""
from datetime import datetime, timedelta
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import F, Max, Q

from ...domain.entities import Connection, Conversation, Message, Template
from .models import ConnectionModel, ConversationModel, MessageModel, TemplateModel, WebhookEventModel

LEASE = timedelta(minutes=5)


def _connection(row: ConnectionModel) -> Connection:
    return Connection(row.id, row.company_id, row.waba_id, row.phone_number_id, row.display_phone, row.secret_ref,
                      row.app_secret_ref, row.verify_token, row.status, row.status_reason)


def _message(row: MessageModel) -> Message:
    return Message(row.id, row.company_id, row.connection_id, row.conversation_id, row.direction, row.type,
                   row.content, row.status, row.provider_message_id, row.template_id, row.pricing_category,
                   row.billable, row.pricing_model, row.cost, row.currency, row.sent_at, row.attempts,
                   row.next_attempt_at, row.failure_reason, row.created_at)


def _template(row: TemplateModel) -> Template:
    return Template(row.id, row.name, row.language, row.category, row.status, row.components, row.synced_at)


def _conversation(row: ConversationModel) -> Conversation:
    return Conversation(row.id, row.company_id, row.connection_id, row.phone, row.last_inbound_at, row.owner_id,
                        row.customer_id, row.lead_id, row.opportunity_id)


class DjangoConnectionRepository:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get(self) -> Connection | None:
        row = ConnectionModel.objects.filter(company_id=self.company_id).first()
        return _connection(row) if row else None

    def save(self, c: Connection) -> Connection:
        row, _ = ConnectionModel.objects.update_or_create(company_id=self.company_id, defaults={
            'waba_id': c.waba_id, 'phone_number_id': c.phone_number_id, 'display_phone': c.display_phone,
            'secret_ref': c.secret_ref, 'app_secret_ref': c.app_secret_ref, 'verify_token': c.verify_token,
            'status': c.status, 'status_reason': c.status_reason})
        return _connection(row)

    def phone_number_taken(self, phone_number_id: str) -> bool:
        return ConnectionModel.objects.filter(phone_number_id=phone_number_id).exclude(
            company_id=self.company_id).exists()


class ConnectionDirectory:
    """Búsquedas entre empresas por datos que envía Meta (número o verify token)."""

    @staticmethod
    def by_phone_number_id(phone_number_id: str) -> Connection | None:
        row = ConnectionModel.objects.filter(phone_number_id=phone_number_id).first()
        return _connection(row) if row else None

    @staticmethod
    def verify_token_exists(token: str) -> bool:
        return bool(token) and ConnectionModel.objects.filter(verify_token=token).exclude(status='disabled').exists()

    @staticmethod
    def by_id(connection_id: UUID) -> Connection | None:
        row = ConnectionModel.objects.filter(id=connection_id).first()
        return _connection(row) if row else None

    @staticmethod
    def mark(connection: Connection) -> None:
        ConnectionModel.objects.filter(id=connection.id).update(status=connection.status,
                                                                status_reason=connection.status_reason)


class DjangoConversationRepository:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get_or_create(self, connection_id: UUID, phone: str) -> Conversation:
        row, _ = ConversationModel.objects.get_or_create(
            company_id=self.company_id, connection_id=connection_id, phone=phone)
        return _conversation(row)

    def get(self, conversation_id: UUID) -> Conversation:
        return _conversation(ConversationModel.objects.get(company_id=self.company_id, id=conversation_id))

    def find(self, conversation_id: UUID) -> Conversation | None:
        row = ConversationModel.objects.filter(company_id=self.company_id, id=conversation_id).first()
        return _conversation(row) if row else None

    def save(self, c: Conversation) -> None:
        """Solo la ventana: el worker no debe pisar el responsable ni los vínculos que otro usuario acaba de fijar."""
        ConversationModel.objects.filter(company_id=self.company_id, id=c.id).update(last_inbound_at=c.last_inbound_at)

    def save_links(self, c: Conversation) -> None:
        """Solo responsable y vínculos: asignar no debe pisar `last_inbound_at` de un mensaje que llega a la vez."""
        ConversationModel.objects.filter(company_id=self.company_id, id=c.id).update(
            owner_id=c.owner_id, customer_id=c.customer_id, lead_id=c.lead_id, opportunity_id=c.opportunity_id)

    def page(self, *, owner_id: int | None, unassigned: bool, opportunity_id: UUID | None, search: str | None,
             customer_ids, lead_ids, offset: int, limit: int) -> tuple[int, list[Conversation], dict]:
        """Conversaciones por último mensaje (más reciente primero) y su último mensaje, en dos consultas."""
        rows = ConversationModel.objects.filter(company_id=self.company_id)
        if owner_id is not None:
            rows = rows.filter(owner_id=owner_id)
        if unassigned:
            rows = rows.filter(owner_id__isnull=True)
        if opportunity_id is not None:
            rows = rows.filter(opportunity_id=opportunity_id)
        if search:
            digits = ''.join(ch for ch in search if ch.isdigit())
            condition = Q(customer_id__in=list(customer_ids)) | Q(lead_id__in=list(lead_ids))
            if digits:
                condition |= Q(phone__contains=digits)
            rows = rows.filter(condition)
        rows = rows.annotate(last_at=Max('messages__created_at')).order_by(F('last_at').desc(nulls_last=True), 'id')
        total = rows.count()
        page = list(rows[offset:offset + limit])
        last = {}
        if page:
            latest = (MessageModel.objects.filter(company_id=self.company_id, conversation_id__in=[r.id for r in page])
                      .order_by('conversation_id', '-created_at', '-id').distinct('conversation_id'))
            last = {m.conversation_id: _message(m) for m in latest}
        return total, [_conversation(r) for r in page], last

    def last_message(self, conversation_id: UUID) -> Message | None:
        row = (MessageModel.objects.filter(company_id=self.company_id, conversation_id=conversation_id)
               .order_by('-created_at', '-id').first())
        return _message(row) if row else None


class DjangoMessageRepository:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _fields(self, m: Message) -> dict:
        return {'company_id': self.company_id, 'connection_id': m.connection_id,
                'conversation_id': m.conversation_id, 'provider_message_id': m.provider_message_id,
                'direction': m.direction, 'type': m.type, 'content': m.content, 'template_id': m.template_id,
                'status': m.status, 'pricing_category': m.pricing_category, 'billable': m.billable,
                'pricing_model': m.pricing_model, 'cost': m.cost, 'currency': m.currency, 'sent_at': m.sent_at,
                'attempts': m.attempts, 'next_attempt_at': m.next_attempt_at, 'failure_reason': m.failure_reason}

    def add(self, m: Message) -> Message:
        return _message(MessageModel.objects.create(id=m.id, **self._fields(m)))

    def add_inbound_once(self, m: Message) -> tuple[Message, bool]:
        """Inserta; si el wamid ya existe en la conexión devuelve el existente y `False` (idempotencia)."""
        try:
            with transaction.atomic():
                return self.add(m), True
        except IntegrityError:
            row = MessageModel.objects.get(company_id=self.company_id, connection_id=m.connection_id,
                                           provider_message_id=m.provider_message_id)
            return _message(row), False

    def by_provider_id(self, connection_id: UUID, wamid: str) -> Message | None:
        row = MessageModel.objects.filter(company_id=self.company_id, connection_id=connection_id,
                                          provider_message_id=wamid).first()
        return _message(row) if row else None

    def get(self, message_id: UUID) -> Message | None:
        row = MessageModel.objects.filter(company_id=self.company_id, id=message_id).first()
        return _message(row) if row else None

    def thread(self, conversation_id: UUID, after: datetime | None, limit: int) -> list[Message]:
        """Mensajes de la conversación en orden cronológico; con `after` solo los creados desde esa fecha (incl.)."""
        rows = MessageModel.objects.filter(company_id=self.company_id, conversation_id=conversation_id)
        if after is not None:
            rows = rows.filter(created_at__gte=after)
            return [_message(r) for r in rows.order_by('created_at', 'id')[:limit]]
        newest = list(rows.order_by('-created_at', '-id')[:limit])
        return [_message(r) for r in reversed(newest)]

    def save(self, m: Message) -> None:
        MessageModel.objects.filter(company_id=self.company_id, id=m.id).update(**{
            k: v for k, v in self._fields(m).items() if k not in ('company_id', 'connection_id', 'conversation_id')})


class DjangoTemplateRepository:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get(self, template_id: UUID) -> Template | None:
        row = TemplateModel.objects.filter(company_id=self.company_id, id=template_id).first()
        return _template(row) if row else None

    def all(self) -> list[Template]:
        return [_template(r) for r in TemplateModel.objects.filter(company_id=self.company_id)]

    def replace_all(self, connection_id: UUID, rows: list[dict], now: datetime) -> list[Template]:
        with transaction.atomic():
            keep = []
            for r in rows:
                obj, _ = TemplateModel.objects.update_or_create(
                    connection_id=connection_id, name=r['name'], language=r['language'],
                    defaults={'company_id': self.company_id, 'category': r['category'], 'status': r['status'],
                              'components': r['components'], 'synced_at': now})
                keep.append(obj.id)
            TemplateModel.objects.filter(company_id=self.company_id, connection_id=connection_id).exclude(
                id__in=keep).delete()
        return self.all()


class EventQueue:
    """Cola de eventos de webhook verificados."""

    @staticmethod
    def add(connection: Connection, payload) -> None:
        WebhookEventModel.objects.create(company_id=connection.company_id, connection_id=connection.id,
                                         payload=payload)

    @staticmethod
    def claim_next(now: datetime):
        """Reclama el siguiente evento (o uno `processing` abandonado hace más de 10 min)."""
        with transaction.atomic():
            row = (WebhookEventModel.objects.select_for_update(skip_locked=True)
                   .filter(status='pending').order_by('created_at', 'id').first()
                   or WebhookEventModel.objects.select_for_update(skip_locked=True)
                   .filter(status='processing', claimed_at__lt=now - timedelta(minutes=10)).first())
            if row is None:
                return None
            row.status, row.claimed_at = 'processing', now
            row.save(update_fields=['status', 'claimed_at'])
            return row.id, row.connection_id, row.payload

    @staticmethod
    def finish(event_id: UUID, now: datetime, error: str = '') -> None:
        WebhookEventModel.objects.filter(id=event_id).update(
            status='failed' if error else 'done', failure_reason=error[:500], processed_at=now)


class OutboxQueue:
    """Mensajes salientes `queued` listos para enviar (con arrendamiento para no duplicar envíos)."""

    @staticmethod
    def claim_next(now: datetime):
        with transaction.atomic():
            row = (MessageModel.objects.select_for_update(skip_locked=True)
                   .filter(status='queued', direction='out').filter(Q(next_attempt_at__isnull=True)
                                                                    | Q(next_attempt_at__lte=now))
                   .order_by('created_at', 'id').first())
            if row is None:
                return None
            MessageModel.objects.filter(id=row.id).update(next_attempt_at=now + LEASE)
            return row.company_id, row.id
