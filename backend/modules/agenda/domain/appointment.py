"""Cita: estados, transiciones y reglas de horario puras (sin Django)."""
from dataclasses import dataclass
from datetime import datetime

SCHEDULED = 'scheduled'
CONFIRMED = 'confirmed'
CANCELLED = 'cancelled'
ATTENDED = 'attended'
NO_SHOW = 'no_show'

STATUSES = (SCHEDULED, CONFIRMED, CANCELLED, ATTENDED, NO_SHOW)
OCCUPYING = (SCHEDULED, CONFIRMED)
REASON_MAX = 500


class AppointmentRuleError(Exception):
    """Regla de negocio incumplida; `field` indica el campo afectado cuando aplica."""

    def __init__(self, message: str, field: str = 'non_field_errors', code: str = 'invalid'):
        self.message = message
        self.field = field
        # Código estable: el cliente traduce el mensaje a su idioma a partir de él.
        self.code = code
        super().__init__(message)


class InvalidTransition(AppointmentRuleError):
    def __init__(self, message: str, field: str = 'non_field_errors', code: str = 'invalid_transition'):
        super().__init__(message, field, code)


def clean_reason(reason) -> str:
    value = reason.strip() if isinstance(reason, str) else ''
    if not value:
        raise AppointmentRuleError('El motivo es obligatorio.', 'reason', 'reason_required')
    if len(value) > REASON_MAX:
        raise AppointmentRuleError(f'No puede superar {REASON_MAX} caracteres.', 'reason', 'reason_too_long')
    return value


def intervals_overlap(first_start: datetime, first_end: datetime, second_start: datetime, second_end: datetime) -> bool:
    """Intervalos semiabiertos: 09:00–09:30 y 09:30–10:00 no se solapan."""
    return first_start < second_end and second_start < first_end


def fits_in(starts: datetime, ends: datetime, available: list[tuple[datetime, datetime]]) -> bool:
    """La cita completa debe caber en un único intervalo disponible."""
    return any(left <= starts and ends <= right for left, right in available)


@dataclass
class Appointment:
    status: str
    starts: datetime
    ends: datetime

    def occupies(self) -> bool:
        return self.status in OCCUPYING

    def allowed_actions(self, now: datetime) -> list[str]:
        if not self.occupies():
            return []
        actions = ['reschedule', 'cancel']
        if self.status == SCHEDULED:
            actions.insert(0, 'confirm')
        if now >= self.starts:
            actions += ['attend', 'no_show']
        return actions

    def _require(self, action: str, now: datetime | None = None) -> None:
        if action not in self.allowed_actions(now or self.starts):
            raise InvalidTransition('La cita no admite esta acción en su estado actual.')

    def confirm(self) -> None:
        self._require('confirm')
        self.status = CONFIRMED

    def reschedule(self, starts: datetime, ends: datetime) -> tuple[datetime, datetime]:
        """Devuelve el horario anterior. Conserva el estado."""
        self._require('reschedule')
        if starts >= ends:
            raise AppointmentRuleError('El fin debe ser posterior al inicio.', 'starts', 'ends_before_start')
        previous = (self.starts, self.ends)
        self.starts, self.ends = starts, ends
        return previous

    def cancel(self) -> None:
        self._require('cancel')
        self.status = CANCELLED

    def mark_attended(self, now: datetime) -> None:
        self._require('attend', now)
        self.status = ATTENDED

    def mark_no_show(self, now: datetime) -> None:
        self._require('no_show', now)
        self.status = NO_SHOW
