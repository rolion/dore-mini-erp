from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid4

from .account import NAME_MAX_LENGTH, AccountValidationError, validate_name

OPEN = 'OPEN'
CLOSED = 'CLOSED'
STATUSES = (OPEN, CLOSED)


class FiscalPeriodValidationError(AccountValidationError):
    """Datos inválidos de un período; `errors` mapea campo -> mensajes."""


class FiscalPeriodNotFound(Exception):
    pass


class FiscalPeriodConflict(Exception):
    """La acción choca con el estado de otros datos; `periods` lista los nombres de los períodos implicados."""

    def __init__(self, code: str, message: str, periods: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.periods = periods or []


class FiscalPeriodContractError(Exception):
    """El contrato se usó mal (p. ej. contabilizar fuera de la transacción del asiento)."""


class DateOutsideFiscalPeriod(Exception):
    """La fecha contable no pertenece a ningún período fiscal de la empresa."""

    def __init__(self, accounting_date: date):
        super().__init__(f'La fecha {accounting_date.isoformat()} no está dentro de ningún período fiscal.')
        self.accounting_date = accounting_date


class FiscalPeriodClosed(Exception):
    """La fecha contable cae en un período cerrado."""

    def __init__(self, name: str, accounting_date: date):
        super().__init__(f'El período «{name}» está cerrado; no se puede contabilizar el {accounting_date.isoformat()}.')
        self.name = name
        self.accounting_date = accounting_date


def _date(field: str, value: object) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise FiscalPeriodValidationError({field: ['La fecha no es válida.']})
    return value


def _limits(start: object, end: object) -> tuple[date, date]:
    start, end = _date('start_date', start), _date('end_date', end)
    if start > end:
        raise FiscalPeriodValidationError({'end_date': ['La fecha de fin no puede ser anterior a la de inicio.']})
    return start, end


@dataclass
class FiscalPeriod:
    """Rango inclusivo de fechas de una empresa. Cerrado, no admite cambios hasta reabrirlo."""
    id: UUID
    name: str
    start_date: date
    end_date: date
    status: str = OPEN
    closed_at: datetime | None = None
    closed_by_name: str = ''
    reopened_at: datetime | None = None
    reopened_by_name: str = ''
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, name: object, start_date: object, end_date: object) -> 'FiscalPeriod':
        start, end = _limits(start_date, end_date)
        return cls(id=uuid4(), name=validate_name(name), start_date=start, end_date=end)

    @property
    def is_open(self) -> bool:
        return self.status == OPEN

    def contains(self, day: date) -> bool:
        return self.start_date <= day <= self.end_date

    def overlaps(self, start: date, end: date) -> bool:
        return self.start_date <= end and start <= self.end_date

    def _require_open(self) -> None:
        if not self.is_open:
            raise FiscalPeriodConflict('period_closed', f'El período «{self.name}» está cerrado: reábrelo para modificarlo.')

    def rename(self, name: object) -> None:
        self._require_open()
        self.name = validate_name(name)

    def change_limits(self, start_date: object, end_date: object) -> None:
        self._require_open()
        self.start_date, self.end_date = _limits(start_date, end_date)

    def close(self, by: str, at: datetime) -> None:
        if not self.is_open:
            raise FiscalPeriodConflict('period_invalid_state', f'El período «{self.name}» ya está cerrado.')
        self.status, self.closed_at, self.closed_by_name = CLOSED, at, by

    def reopen(self, by: str, at: datetime) -> None:
        if self.is_open:
            raise FiscalPeriodConflict('period_invalid_state', f'El período «{self.name}» ya está abierto.')
        self.status, self.reopened_at, self.reopened_by_name = OPEN, at, by


__all__ = ['CLOSED', 'NAME_MAX_LENGTH', 'OPEN', 'STATUSES', 'DateOutsideFiscalPeriod', 'FiscalPeriod',
           'FiscalPeriodClosed', 'FiscalPeriodConflict', 'FiscalPeriodContractError', 'FiscalPeriodNotFound',
           'FiscalPeriodValidationError']
