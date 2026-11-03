"""Casos de uso de citas: todas las escrituras serializan por profesional con el bloqueo de `Schedule`."""
from datetime import date, datetime, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from modules.agenda.application.week import week_availability, week_records
from modules.agenda.domain.appointment import (
    OCCUPYING, Appointment as AppointmentState, AppointmentRuleError, clean_reason, fits_in,
)
from modules.agenda.domain.schedule import subtract
from modules.agenda.infrastructure.adapters import (
    get_customer_for_sale, get_service_for_new_use, professional_exists,
)
from modules.agenda.models import Appointment, AppointmentEvent, Schedule

ZONE = ZoneInfo('America/La_Paz')


class Actor(NamedTuple):
    """Usuario que ejecuta la acción: el id se conserva y el nombre se guarda para mostrarlo sin consultar otro módulo."""

    id: int
    name: str


class AppointmentConflict(Exception):
    """El horario ya no está disponible o la cita cambió de estado; el servidor es la autoridad."""

    def __init__(self, message: str, code: str = 'schedule_conflict'):
        self.message = message
        self.code = code
        super().__init__(message)


class AppointmentNotFound(Exception):
    pass


def _lock(company_id, professional_id) -> None:
    schedule, _ = Schedule.objects.get_or_create(company_id=company_id, professional_id=professional_id)
    Schedule.objects.filter(pk=schedule.pk).update(company_id=F('company_id'))


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def available_intervals(company_id, professional_id, first: date, last: date) -> list[tuple[datetime, datetime]]:
    """Intervalos de disponibilidad (turno − pausas − ausencias) entre dos fechas locales inclusive."""
    intervals: list[tuple[datetime, datetime]] = []
    week = _monday(first)
    while week <= last:
        shifts, absences = week_records(company_id, professional_id, week, ZONE)
        _, availability = week_availability(shifts, absences, week, ZONE)
        intervals += [(datetime.fromisoformat(i['starts']), datetime.fromisoformat(i['ends'])) for i in availability]
        week += timedelta(days=7)
    return sorted(intervals)


def free_slots(company_id, professional_id, first: date, last: date, minutes: int | None = None):
    """Disponibilidad menos las citas que ocupan horario; opcionalmente solo tramos de al menos `minutes`."""
    start = datetime.combine(first, datetime.min.time(), ZONE)
    end = datetime.combine(last + timedelta(days=1), datetime.min.time(), ZONE)
    busy = sorted(Appointment.objects.filter(
        company_id=company_id, professional_id=professional_id, status__in=OCCUPYING,
        starts__lt=end, ends__gt=start,
    ).values_list('starts', 'ends'))
    result = []
    for left, right in available_intervals(company_id, professional_id, first, last):
        for free_left, free_right in subtract(left, right, busy):
            if minutes is None or free_right - free_left >= timedelta(minutes=minutes):
                result.append({'starts': free_left.astimezone(ZONE).isoformat(),
                               'ends': free_right.astimezone(ZONE).isoformat()})
    return result


def _ensure_placement(company_id, professional_id, starts, ends, exclude_id=None) -> None:
    local_start, local_end = starts.astimezone(ZONE), ends.astimezone(ZONE)
    if local_start.date() != local_end.date():
        raise AppointmentRuleError('La cita debe terminar el mismo día en que empieza.', 'starts')
    available = available_intervals(company_id, professional_id, local_start.date(), local_start.date())
    if not fits_in(starts, ends, available):
        raise AppointmentRuleError(
            'El horario queda fuera del turno del profesional, en una pausa o en una ausencia.', 'starts')
    clash = Appointment.objects.filter(
        company_id=company_id, professional_id=professional_id, status__in=OCCUPYING,
        starts__lt=ends, ends__gt=starts,
    ).exclude(pk=exclude_id)
    if clash.exists():
        raise AppointmentConflict('El profesional ya tiene una cita en ese horario.')


def _event(appointment, kind, actor, reason='', previous=None) -> None:
    AppointmentEvent.objects.create(
        appointment=appointment, kind=kind, author_id=actor.id, author_name=actor.name, reason=reason,
        previous_starts=previous[0] if previous else None, previous_ends=previous[1] if previous else None,
    )


def _state(appointment) -> AppointmentState:
    return AppointmentState(appointment.status, appointment.starts, appointment.ends)


def allowed_actions(appointment) -> list[str]:
    return _state(appointment).allowed_actions(timezone.now())


@transaction.atomic
def create(company_id, actor, *, professional_id, customer_id, service_id, starts, duration_minutes, notes=''):
    if not professional_exists(company_id, professional_id):
        raise AppointmentRuleError('Profesional no encontrado.', 'professional_id')
    customer = get_customer_for_sale(company_id, customer_id)
    if customer is None or not customer.active:
        raise AppointmentRuleError('Selecciona un cliente activo de tu empresa.', 'customer_id')
    service = get_service_for_new_use(company_id, service_id)
    if service is None:
        raise AppointmentRuleError('Selecciona un servicio activo.', 'service_id')
    ends = starts + timedelta(minutes=duration_minutes)
    _lock(company_id, professional_id)
    _ensure_placement(company_id, professional_id, starts, ends)
    appointment = Appointment.objects.create(
        company_id=company_id, professional_id=professional_id, customer_id=customer.id,
        customer_name=customer.name, service_id=service.id, service_name=service.name,
        starts=starts, ends=ends, duration_minutes=duration_minutes, notes=notes.strip(), created_by=actor.id,
    )
    _event(appointment, 'created', actor)
    return appointment


def _locked(company_id, appointment_id) -> Appointment:
    appointment = Appointment.objects.filter(company_id=company_id, pk=appointment_id).first()
    if appointment is None:
        raise AppointmentNotFound()
    _lock(company_id, appointment.professional_id)
    return Appointment.objects.select_for_update().get(pk=appointment.pk)


def _apply(appointment, state) -> None:
    appointment.status, appointment.starts, appointment.ends = state.status, state.starts, state.ends
    appointment.duration_minutes = int((state.ends - state.starts).total_seconds() // 60)
    appointment.save()


def _transition(company_id, actor, appointment_id, kind, action, reason=None):
    clean = clean_reason(reason) if reason is not None else ''
    appointment = _locked(company_id, appointment_id)
    state = _state(appointment)
    try:
        action(state)
    except AppointmentRuleError as exc:
        raise AppointmentConflict(exc.message, 'invalid_transition') from exc
    _apply(appointment, state)
    _event(appointment, kind, actor, clean)
    return appointment


@transaction.atomic
def confirm(company_id, actor, appointment_id):
    return _transition(company_id, actor, appointment_id, 'confirmed', lambda s: s.confirm())


@transaction.atomic
def cancel(company_id, actor, appointment_id, reason):
    return _transition(company_id, actor, appointment_id, 'cancelled', lambda s: s.cancel(), reason or '')


@transaction.atomic
def mark_attended(company_id, actor, appointment_id):
    return _transition(company_id, actor, appointment_id, 'attended',
                       lambda s: s.mark_attended(timezone.now()))


@transaction.atomic
def mark_no_show(company_id, actor, appointment_id):
    return _transition(company_id, actor, appointment_id, 'no_show',
                       lambda s: s.mark_no_show(timezone.now()))


@transaction.atomic
def reschedule(company_id, actor, appointment_id, starts, duration_minutes, reason):
    clean = clean_reason(reason)
    appointment = _locked(company_id, appointment_id)
    state = _state(appointment)
    ends = starts + timedelta(minutes=duration_minutes or appointment.duration_minutes)
    try:
        previous = state.reschedule(starts, ends)
    except AppointmentRuleError as exc:
        if exc.field == 'non_field_errors':
            raise AppointmentConflict(exc.message, 'invalid_transition') from exc
        raise
    _ensure_placement(company_id, appointment.professional_id, starts, ends, appointment.pk)
    _apply(appointment, state)
    _event(appointment, 'rescheduled', actor, clean, previous)
    return appointment


@transaction.atomic
def update_notes(company_id, appointment_id, notes):
    appointment = _locked(company_id, appointment_id)
    if appointment.status not in OCCUPYING:
        raise AppointmentConflict('La cita ya no admite cambios.', 'invalid_transition')
    appointment.notes = notes.strip()
    appointment.save(update_fields=['notes', 'updated_at'])
    return appointment
