"""Reportes «Proformas por cobrar» y «Proformas pagadas» (solo lectura).

Universo: proformas presentadas vigentes con importe aceptado mayor que cero, filtradas por la fecha de la proforma.
Lo cobrado se lee de Cobros por un puerto (`collections.paid_totals`); el doctor, de Personal (`professionals.names`).
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from modules.dentistry.domain.proforma import money

RECEIVABLE, PAID = 'receivable', 'paid'
KINDS = (RECEIVABLE, PAID)
_ZERO = Decimal('0')


@dataclass(frozen=True)
class ProformaReportRow:
    id: UUID
    number: str
    date: date
    patient_id: UUID
    patient_name: str
    professional_id: UUID | None
    professional_name: str
    amount: Decimal  # por cobrar: saldo pendiente; pagadas: total cobrado


@dataclass(frozen=True)
class ProformaReport:
    rows: list[ProformaReportRow]
    total: Decimal

    @property
    def count(self) -> int:
        return len(self.rows)


class ProformaReports:
    def __init__(self, repository, collections, professionals):
        self.repository, self.collections, self.professionals = repository, collections, professionals

    def execute(self, kind: str, date_from: date | None = None, date_to: date | None = None) -> ProformaReport:
        if kind not in KINDS:
            raise ValueError(kind)
        proformas = [p for p in self.repository.presented_between(date_from, date_to)
                     if p.totals['accepted'] > 0]
        paid = self.collections.paid_totals(p.number for p in proformas)
        names = self.professionals.names({p.professional_id for p in proformas if p.professional_id})
        rows = []
        for proforma in proformas:
            accepted, collected = proforma.totals['accepted'], money(paid.get(proforma.number, _ZERO))
            if kind == RECEIVABLE and collected < accepted:
                amount = money(accepted - collected)
            elif kind == PAID and collected >= accepted:
                amount = collected
            else:
                continue
            rows.append(ProformaReportRow(
                proforma.id, proforma.number, proforma.date, proforma.customer_id, proforma.patient_name,
                proforma.professional_id, names.get(proforma.professional_id, '') if proforma.professional_id else '',
                amount))
        rows.sort(key=lambda r: (r.date, r.number), reverse=True)
        return ProformaReport(rows, money(sum((r.amount for r in rows), _ZERO)))
