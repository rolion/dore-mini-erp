"""Fachada pública de Agenda para otros módulos (Odontología, PB-ODO-007).

Devuelve DTO inmutables, nunca modelos. Todo filtra por `company_id`. Los comandos `*_by_clinic` los usa el flujo
clínico, que ya validó la atención: no pasan por las guardas de Agenda.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from modules.agenda.application import appointments as service
from modules.agenda.application.appointments import Actor, AppointmentConflict, AppointmentNotFound, ZONE
from modules.agenda.application.guards import AppointmentRef, Veto, register_guard  # noqa: F401
from modules.agenda.domain.appointment import AppointmentRuleError, appointment_code
from modules.agenda.models import Appointment

__all__ = ['Actor', 'AppointmentConflict', 'AppointmentNotFound', 'AppointmentRuleError', 'AppointmentRef',
           'AppointmentSnapshot', 'Veto', 'ZONE', 'appointments_in_range', 'attend_by_clinic', 'cancel_by_clinic',
           'get_appointment', 'get_appointments', 'lock_appointment', 'register_guard']


@dataclass(frozen=True)
class AppointmentSnapshot:
    id: UUID
    customer_id: UUID
    customer_name: str
    professional_id: UUID
    service_name: str
    starts: datetime
    ends: datetime
    status: str
    allowed_actions: tuple[str, ...]
    notes: str
    code: str | None = None  # `C-000001`; None en citas anteriores a la serie
    fiscal_period_name: str = ''


def _snapshot(row: Appointment) -> AppointmentSnapshot:
    return AppointmentSnapshot(
        row.id, row.customer_id, row.customer_name, row.professional_id, row.service_name, row.starts, row.ends,
        row.status, tuple(service.allowed_actions(row)), row.notes, appointment_code(row.number),
        row.fiscal_period_name)


def get_appointment(company_id: UUID, appointment_id: UUID) -> AppointmentSnapshot | None:
    row = Appointment.objects.filter(company_id=company_id, pk=appointment_id).first()
    return _snapshot(row) if row else None


def get_appointments(company_id: UUID, ids: Iterable[UUID]) -> dict[UUID, AppointmentSnapshot]:
    rows = Appointment.objects.filter(company_id=company_id, pk__in=set(ids))
    return {row.id: _snapshot(row) for row in rows}


def lock_appointment(company_id: UUID, appointment_id: UUID) -> AppointmentSnapshot:
    """Bloquea la cita (y la agenda de su profesional); usar dentro de una transacción."""
    return _snapshot(service._locked(company_id, appointment_id))


def appointments_in_range(company_id: UUID, *, first_day: date, last_day: date, professional_id=None,
                          status=None) -> list[AppointmentSnapshot]:
    """Citas cuyo inicio cae en el rango local [first_day, last_day], ordenadas; el llamador acota el rango."""
    rows = Appointment.objects.filter(
        company_id=company_id,
        starts__gte=datetime.combine(first_day, datetime.min.time(), ZONE),
        starts__lt=datetime.combine(last_day + timedelta(days=1), datetime.min.time(), ZONE))
    if professional_id:
        rows = rows.filter(professional_id=professional_id)
    if status:
        rows = rows.filter(status=status)
    return [_snapshot(row) for row in rows.order_by('starts', 'id')]


def attend_by_clinic(company_id: UUID, actor: Actor, appointment_id: UUID) -> None:
    service.mark_attended(company_id, actor, appointment_id, clinical=True)


def cancel_by_clinic(company_id: UUID, actor: Actor, appointment_id: UUID, reason: str) -> None:
    service.cancel(company_id, actor, appointment_id, reason, clinical=True)
