"""Composición: gateway por conexión, reloj y servicios con la empresa dada."""
from datetime import datetime, timezone

from django.conf import settings

from ..application.services import ProcessWebhookEvent, SendMessages
from .django.repositories import (
    DjangoConnectionRepository,
    DjangoConversationRepository,
    DjangoMessageRepository,
    DjangoTemplateRepository,
)
from .fake_gateway import FakeMessagingGateway
from .secrets import EnvSecretResolver
from .whatsapp_adapter import WhatsAppCloudAdapter


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)


def gateway_for(connection):
    if settings.MESSAGING_PROVIDER == 'fake':
        return FakeMessagingGateway()
    return WhatsAppCloudAdapter(EnvSecretResolver().get(connection.secret_ref), connection.phone_number_id,
                                connection.waba_id, base_url=settings.WHATSAPP_API_BASE_URL,
                                api_version=settings.WHATSAPP_API_VERSION)


def send_service(company_id) -> SendMessages:
    return SendMessages(company_id, DjangoConnectionRepository(company_id), DjangoConversationRepository(company_id),
                        DjangoMessageRepository(company_id), DjangoTemplateRepository(company_id), SystemClock(),
                        settings.DEFAULT_PHONE_COUNTRY_CODE)


def event_processor(connection) -> ProcessWebhookEvent:
    company_id = connection.company_id
    return ProcessWebhookEvent(connection, DjangoMessageRepository(company_id),
                               DjangoConversationRepository(company_id), SystemClock(),
                               settings.DEFAULT_PHONE_COUNTRY_CODE)
