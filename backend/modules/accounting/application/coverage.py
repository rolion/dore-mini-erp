from dataclasses import dataclass
from datetime import date

from modules.accounting.domain.account import AccountConflict
from modules.accounting.domain.coverage import (
    CoverageStatus,
    Gap,
    coverage_status,
    gaps,
    validate_cutoff,
)


@dataclass(frozen=True)
class SettingsView:
    cutoff_date: date | None
    enabled_at: date | None
    locked: bool  # hay movimientos: el corte ya no cambia
    gaps: list[Gap]


class EnsureSettings:
    """Garantiza corte y tramo vigente de una empresa con Contabilidad habilitada (idempotente).

    Corte nuevo: fecha de pago de su primera entrada si ya tiene libro (empresas anteriores al corte) o hoy.
    Un corte existente nunca se modifica.
    """

    def __init__(self, coverage, entries, today: date):
        self.coverage = coverage
        self.entries = entries
        self.today = today

    def execute(self) -> date:
        cutoff = self.coverage.cutoff_date()
        if cutoff is None:
            cutoff = self.coverage.create_cutoff(self.entries.first_payment_date() or self.today)
        if not self.coverage.has_open_period():
            self.coverage.open_period()
        return cutoff


class OnAccountingEnabled(EnsureSettings):
    """Gancho de habilitación: crea el corte la primera vez y abre un tramo; reactivar no toca el corte."""


class OnAccountingDisabled:
    """Gancho de deshabilitación: completa el corte y el tramo de una empresa anterior que aún no los tenía y lo cierra.

    Así la reactivación posterior deja un periodo sin cobertura aunque nadie hubiera entrado antes a Contabilidad.
    """

    def __init__(self, coverage, entries, today: date):
        self.coverage = coverage
        self.entries = entries
        self.today = today

    def execute(self) -> None:
        EnsureSettings(self.coverage, self.entries, self.today).execute()
        self.coverage.close_period()


class GetSettings:
    def __init__(self, coverage, entries, today: date, enabled: bool):
        self.coverage = coverage
        self.entries = entries
        self.today = today
        self.enabled = enabled

    def execute(self) -> SettingsView:
        if self.enabled:
            EnsureSettings(self.coverage, self.entries, self.today).execute()
        cutoff = self.coverage.cutoff_date()
        periods = self.coverage.periods()
        return SettingsView(cutoff, periods[0].started_on if periods else None,
                            self.entries.has_entries(), gaps(periods))


class UpdateCutoff:
    def __init__(self, coverage, entries, today: date, enabled: bool):
        self.coverage = coverage
        self.entries = entries
        self.today = today
        self.enabled = enabled

    def execute(self, cutoff: object) -> SettingsView:
        if self.enabled:
            EnsureSettings(self.coverage, self.entries, self.today).execute()
        if self.coverage.cutoff_date() is None:
            raise AccountConflict('accounting_disabled', 'Habilita Contabilidad antes de definir la fecha de corte.')
        value = validate_cutoff(cutoff, self.today)
        if self.entries.has_entries():
            if value != self.coverage.cutoff_date():
                raise AccountConflict('cutoff_locked',
                                      'No se puede cambiar la fecha de corte: la empresa ya tiene movimientos.')
        else:
            self.coverage.set_cutoff(value)
        return GetSettings(self.coverage, self.entries, self.today, False).execute()


class GetCoverageStatus:
    def __init__(self, coverage, entries, today: date, enabled: bool):
        self.coverage = coverage
        self.entries = entries
        self.today = today
        self.enabled = enabled

    def execute(self, effective_date: date) -> CoverageStatus:
        if self.enabled:
            EnsureSettings(self.coverage, self.entries, self.today).execute()
        return coverage_status(enabled=self.enabled, cutoff_date=self.coverage.cutoff_date(),
                               periods=self.coverage.periods(), effective_date=effective_date)


class DisableBlockers:
    """Motivos que impiden deshabilitar Contabilidad: egresos vigentes sin revertir (los aporta CONT-02)."""

    def __init__(self, outflows):
        self.outflows = outflows  # puerto: open_count() -> int

    def execute(self) -> list[str]:
        count = self.outflows.open_count()
        if count:
            return [f'Hay {count} egresos contabilizados vigentes; anúlalos o revierte antes de deshabilitar '
                    'Contabilidad.']
        return []
