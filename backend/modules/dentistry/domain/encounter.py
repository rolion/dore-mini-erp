"""Agregado DentalEncounter (atención odontológica, PB-ODO-007). Sin dependencias de Django."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

IN_PROGRESS, FINISHED, CANCELLED = 'in_progress', 'finished', 'cancelled'
PENDING = 'pending'  # derivado: cita sin atención; nunca se persiste
REASON_MAX, OBSERVATIONS_MAX = 500, 2000


class EncounterNotFound(Exception):
    pass


class EncounterStateError(Exception):
    """La acción no procede en el estado actual (409); `code` es estable para que el cliente traduzca."""

    def __init__(self, message: str, code: str = 'invalid_state'):
        super().__init__(message)
        self.code = code


class EncounterValidationError(Exception):
    def __init__(self, errors: dict):
        super().__init__(errors)
        self.errors = errors


def clean_reason(reason) -> str:
    value = reason.strip() if isinstance(reason, str) else ''
    if not value:
        raise EncounterValidationError({'reason': ['El motivo de la cancelación es obligatorio.']})
    if len(value) > REASON_MAX:
        raise EncounterValidationError({'reason': [f'El motivo admite hasta {REASON_MAX} caracteres.']})
    return value


def clean_observations(text) -> str:
    value = text.strip() if isinstance(text, str) else ''
    if len(value) > OBSERVATIONS_MAX:
        raise EncounterValidationError({'observations': [f'Las observaciones admiten hasta {OBSERVATIONS_MAX}.']})
    return value


@dataclass
class Encounter:
    appointment_id: UUID
    customer_id: UUID
    professional_id: UUID
    status: str = IN_PROGRESS
    started_at: datetime | None = None
    finished_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str = ''
    observations: str = ''
    id: UUID | None = None

    def __post_init__(self):
        if self.id is None:
            self.id = uuid4()

    def allowed_actions(self) -> list[str]:
        return ['finish', 'cancel'] if self.status == IN_PROGRESS else []

    def ensure_in_progress(self, what: str = 'La atención') -> None:
        if self.status != IN_PROGRESS:
            label = 'finalizada' if self.status == FINISHED else 'cancelada'
            raise EncounterStateError(f'{what} ya está {label}.', f'encounter_{self.status}')

    def finish(self, now: datetime) -> bool:
        """Devuelve False si ya estaba finalizada (idempotente); una cancelada no se finaliza."""
        if self.status == FINISHED:
            return False
        self.ensure_in_progress()
        self.status, self.finished_at = FINISHED, now
        return True

    def cancel(self, reason, now: datetime) -> None:
        clean = clean_reason(reason)
        self.ensure_in_progress()
        self.status, self.cancelled_at, self.cancellation_reason = CANCELLED, now, clean

    def set_observations(self, text) -> None:
        clean = clean_observations(text)
        self.ensure_in_progress('La atención')
        self.observations = clean
