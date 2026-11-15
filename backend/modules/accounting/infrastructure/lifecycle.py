"""Ganchos del ciclo de vida del módulo `accounting` que se registran en `shared.module_lifecycle`."""
from uuid import UUID

from django.utils import timezone

from modules.accounting.application.coverage import DisableBlockers, OnAccountingDisabled, OnAccountingEnabled

from .django.repositories import DjangoCoverageRepository, DjangoEntryRepository


class DjangoOutflowLedger:
    """Egresos contabilizados vigentes (sin revertir) de una empresa.

    Hasta CONT-02 no existen movimientos de egreso: el conteo es siempre 0. CONT-02 reemplaza esta consulta por la
    real sobre el mismo contrato (`open_count`).
    """

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def open_count(self) -> int:
        return 0


def on_enabled(company_id: UUID) -> None:
    OnAccountingEnabled(DjangoCoverageRepository(company_id), DjangoEntryRepository(company_id),
                        timezone.localdate()).execute()


def on_disabled(company_id: UUID) -> None:
    OnAccountingDisabled(DjangoCoverageRepository(company_id)).execute()


def disable_blockers(company_id: UUID) -> list[str]:
    return DisableBlockers(DjangoOutflowLedger(company_id)).execute()
