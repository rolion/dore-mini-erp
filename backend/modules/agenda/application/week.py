from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from modules.agenda.domain.schedule import subtract


def week_availability(shifts, absences, start: date, zone: ZoneInfo):
    """Devuelve (turnos vigentes, intervalos disponibles) de la semana que empieza en `start`."""
    active_shifts = []
    availability = []
    for shift in shifts:
        day = start + timedelta(days=shift.day)
        if not shift.valid_from <= day <= shift.valid_until:
            continue
        active_shifts.append(shift)
        blocks = [(absence.starts, absence.ends) for absence in absences]
        for pause in shift.breaks:
            blocks.append(tuple(
                datetime.fromisoformat(f'{day}T{pause[key]}').replace(tzinfo=zone) for key in ('starts', 'ends')
            ))
        begins = datetime.combine(day, shift.starts, zone)
        finishes = datetime.combine(day, shift.ends, zone)
        availability.extend(
            {'starts': left.astimezone(zone).isoformat(), 'ends': right.astimezone(zone).isoformat()}
            for left, right in subtract(begins, finishes, blocks)
        )
    return active_shifts, availability
