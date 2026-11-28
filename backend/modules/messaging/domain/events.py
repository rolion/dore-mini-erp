"""Eventos de dominio de la mensajería (nombres en pasado)."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class InboundMessageReceived:
    company_id: UUID
    connection_id: UUID
    conversation_id: UUID
    message_id: UUID
    phone: str
    type: str
    received_at: datetime
