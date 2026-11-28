"""Lectura tolerante de los payloads del webhook de WhatsApp Cloud API (campo `messages`).

Lo desconocido se ignora sin fallar: Meta añade campos y tipos con frecuencia.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class InboundItem:
    wamid: str
    sender: str
    type: str
    content: dict[str, Any]
    at: datetime


@dataclass(frozen=True)
class StatusItem:
    wamid: str
    status: str
    at: datetime
    pricing_category: str = ''
    billable: bool | None = None
    pricing_model: str = ''
    error: str = ''


def phone_number_ids(payload: Any) -> set[str]:
    return {pid for value in _values(payload) if (pid := _metadata_id(value))}


def _values(payload: Any):
    if not isinstance(payload, dict):
        return
    for entry in payload.get('entry') or []:
        for change in (entry.get('changes') or []) if isinstance(entry, dict) else []:
            value = change.get('value') if isinstance(change, dict) else None
            if isinstance(value, dict):
                yield value


def _metadata_id(value: dict) -> str:
    metadata = value.get('metadata')
    return str(metadata.get('phone_number_id') or '') if isinstance(metadata, dict) else ''


def _at(raw: Any) -> datetime:
    try:
        return datetime.fromtimestamp(int(raw), tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return datetime.now(tz=timezone.utc)


def _content(message: dict) -> tuple[str, dict]:
    kind = str(message.get('type') or 'unknown')
    if kind == 'text':
        return kind, {'body': str((message.get('text') or {}).get('body', ''))}
    if kind == 'interactive':
        reply = message.get('interactive') or {}
        chosen = reply.get('button_reply') or reply.get('list_reply') or {}
        return kind, {'id': str(chosen.get('id', '')), 'title': str(chosen.get('title', ''))}
    if kind == 'button':
        return kind, {'body': str((message.get('button') or {}).get('text', ''))}
    return kind, {}


def parse(payload: Any, phone_number_id: str) -> tuple[list[InboundItem], list[StatusItem]]:
    """Mensajes y estados del número `phone_number_id` dentro del payload."""
    inbound: list[InboundItem] = []
    statuses: list[StatusItem] = []
    for value in _values(payload):
        if _metadata_id(value) != phone_number_id:
            continue
        for message in value.get('messages') or []:
            if isinstance(message, dict) and message.get('id') and message.get('from'):
                kind, content = _content(message)
                inbound.append(InboundItem(str(message['id']), str(message['from']), kind, content,
                                           _at(message.get('timestamp'))))
        for status in value.get('statuses') or []:
            if isinstance(status, dict) and status.get('id') and status.get('status'):
                pricing = status.get('pricing') if isinstance(status.get('pricing'), dict) else {}
                errors = status.get('errors') if isinstance(status.get('errors'), list) else []
                first = errors[0] if errors and isinstance(errors[0], dict) else {}
                billable = pricing.get('billable')
                statuses.append(StatusItem(
                    str(status['id']), str(status['status']), _at(status.get('timestamp')),
                    str(pricing.get('category') or ''), billable if isinstance(billable, bool) else None,
                    str(pricing.get('pricing_model') or ''),
                    f"{first.get('code', '')} {first.get('title', '')}".strip()))
    return inbound, statuses
