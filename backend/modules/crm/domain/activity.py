"""Actividad comercial: registro inmutable de lo ocurrido con un cliente u oportunidad (puro). INV-01, INV-06."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from .errors import CrmValidationError
from .task import require_one_related

CHANNELS = ('call', 'whatsapp', 'email', 'visit', 'other')
OUTCOMES = ('contacted', 'no_answer', 'interested', 'not_interested', 'follow_up')
NOTES_MAX = 2000


@dataclass(frozen=True)
class Activity:
    id: UUID
    actor_id: int
    customer_id: UUID | None
    opportunity_id: UUID | None
    channel: str
    outcome: str
    notes: str
    occurred_at: datetime
    task_id: UUID | None = None
    created_at: datetime | None = None

    @classmethod
    def create(cls, *, actor_id: int, customer_id: UUID | None, opportunity_id: UUID | None, channel: object,
               outcome: object, notes: object, occurred_at: datetime | None, now: datetime,
               task_id: UUID | None = None) -> 'Activity':
        errors: dict[str, list[str]] = {}
        try:
            require_one_related(customer_id, opportunity_id)
        except CrmValidationError as exc:
            errors.update(exc.errors)
        if channel not in CHANNELS:
            errors['channel'] = ['Elige un canal válido.']
        outcome = outcome or ''
        if outcome and outcome not in OUTCOMES:
            errors['outcome'] = ['Elige un resultado válido.']
        notes = notes.strip() if isinstance(notes, str) else ''
        if len(notes) > NOTES_MAX:
            errors['notes'] = [f'Usa como máximo {NOTES_MAX} caracteres.']
        if not outcome and not notes and 'outcome' not in errors:
            errors['notes'] = ['Indica un resultado o escribe una nota.']
        when = occurred_at or now
        if when > now:
            errors['occurred_at'] = ['La fecha no puede estar en el futuro.']
        if errors:
            raise CrmValidationError(errors)
        return cls(id=uuid4(), actor_id=actor_id, customer_id=customer_id, opportunity_id=opportunity_id,
                   channel=channel, outcome=outcome, notes=notes, occurred_at=when, task_id=task_id)
