"""Puerto de guardas: otros módulos (p. ej. Odontología) pueden vetar acciones de una cita sin importarse."""
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AppointmentRef:
    id: UUID
    customer_id: UUID


@dataclass(frozen=True)
class Veto:
    code: str
    message: str


Guard = Callable[[UUID, AppointmentRef, str], Veto | None]
_guards: list[Guard] = []


def register_guard(guard: Guard) -> None:
    if guard not in _guards:
        _guards.append(guard)


def first_veto(company_id: UUID, appointment, action: str) -> Veto | None:
    """`action`: attend | no_show | cancel | reschedule. Devuelve el primer veto, o None si nadie se opone."""
    ref = AppointmentRef(appointment.id, appointment.customer_id)
    for guard in _guards:
        veto = guard(company_id, ref, action)
        if veto is not None:
            return veto
    return None
