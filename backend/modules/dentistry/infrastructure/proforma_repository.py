from uuid import UUID

from django.db import transaction
from django.db.models import Prefetch

from modules.dentistry.domain.proforma import DRAFT, PRESENTED, Decision, DentalProforma, DentalProformaLine
from modules.dentistry.infrastructure.proforma_models import (
    DentalProformaCounterModel, DentalProformaDecisionBatchModel, DentalProformaLineDecisionModel,
    DentalProformaLineModel, DentalProformaModel,
)


def _decision(row: DentalProformaLineDecisionModel) -> Decision:
    return Decision(row.id, row.kind, row.decision, row.decided_at, row.recorded_by, row.recorded_by_name,
                    row.accepted_by_name, row.medium, row.reference, row.reason, row.batch_key,
                    row.source_decision_id)


def to_domain(row: DentalProformaModel) -> DentalProforma:
    lines = [DentalProformaLine(l.id, l.service_id, l.description, l.quantity, l.unit_price, l.dental_piece,
                                l.origin_line_id, l.line_kind, tuple(_decision(d) for d in l.decisions.all()))
             for l in row.lines.all()]
    return DentalProforma(row.id, row.number, row.version, row.status, row.customer_id, row.patient_name, row.date,
                          row.valid_until, row.notes, lines, row.created_by)


class DjangoDentalProformaRepository:
    """Toda consulta filtra por la empresa recibida."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _qs(self):
        return DentalProformaModel.objects.filter(company_id=self.company_id).prefetch_related(
            Prefetch('lines', queryset=DentalProformaLineModel.objects.order_by('position')
                     .prefetch_related('decisions')))

    def get(self, proforma_id: UUID, *, for_update: bool = False) -> DentalProforma | None:
        if for_update:  # bloquea solo la cabecera; las líneas se leen después
            if not DentalProformaModel.objects.select_for_update().filter(
                    company_id=self.company_id, pk=proforma_id).exists():
                return None
        row = self._qs().filter(pk=proforma_id).first()
        return to_domain(row) if row else None

    def for_patient(self, customer_id: UUID, *, status: str = ''):
        qs = self._qs().filter(customer_id=customer_id)
        return qs.filter(status=status) if status else qs

    def versions(self, number: str) -> list[DentalProforma]:
        return [to_domain(r) for r in self._qs().filter(number=number).order_by('version')]

    def origin_lines(self, number: str, version: int) -> dict[UUID, DentalProformaLine]:
        """Líneas de la versión anterior, por id (vacío en la versión 1)."""
        row = self._qs().filter(number=number, version=version - 1).first()
        return {line.id: line for line in to_domain(row).lines} if row else {}

    def draft_exists(self, number: str) -> bool:
        return DentalProformaModel.objects.filter(company_id=self.company_id, number=number, status=DRAFT).exists()

    def presented_below(self, number: str, version: int) -> list[DentalProforma]:
        return [to_domain(r) for r in self._qs().filter(number=number, status=PRESENTED, version__lt=version)]

    def next_number(self) -> str:
        """Consecutivo por empresa; el bloqueo de la fila del contador serializa creaciones concurrentes."""
        DentalProformaCounterModel.objects.get_or_create(company_id=self.company_id)
        counter = DentalProformaCounterModel.objects.select_for_update().get(company_id=self.company_id)
        counter.last_number += 1
        counter.save(update_fields=['last_number'])
        return f'ODO-{counter.last_number:06d}'

    # --- idempotencia de decisiones ------------------------------------------------------------------------
    def get_batch(self, key: UUID) -> DentalProformaDecisionBatchModel | None:
        return DentalProformaDecisionBatchModel.objects.filter(
            company_id=self.company_id, idempotency_key=key).first()

    def add_batch(self, key: UUID, proforma_id: UUID, payload_hash: str) -> None:
        DentalProformaDecisionBatchModel.objects.create(
            company_id=self.company_id, idempotency_key=key, proforma_id=proforma_id, payload_hash=payload_hash)

    def save(self, proforma: DentalProforma) -> None:
        """Guarda por diferencia: las líneas conservan su id y el libro de decisiones nunca se reescribe."""
        with transaction.atomic():
            DentalProformaModel.objects.update_or_create(
                id=proforma.id, company_id=self.company_id,
                defaults={'number': proforma.number, 'version': proforma.version, 'status': proforma.status,
                          'customer_id': proforma.customer_id, 'patient_name': proforma.patient_name,
                          'date': proforma.date, 'valid_until': proforma.valid_until, 'notes': proforma.notes,
                          'created_by': proforma.created_by})
            keep = [line.id for line in proforma.lines]
            if proforma.status == DRAFT:  # solo un borrador puede perder líneas
                DentalProformaLineModel.objects.filter(proforma_id=proforma.id).exclude(pk__in=keep).delete()
            for position, line in enumerate(proforma.lines):
                DentalProformaLineModel.objects.update_or_create(
                    id=line.id, proforma_id=proforma.id,
                    defaults={'position': position, 'service_id': line.service_id, 'description': line.description,
                              'quantity': line.quantity, 'unit_price': line.unit_price,
                              'dental_piece': line.dental_piece, 'origin_line_id': line.origin_line_id,
                              'line_kind': line.line_kind})
                self._save_decisions(proforma, line)

    def _save_decisions(self, proforma: DentalProforma, line: DentalProformaLine) -> None:
        ids = [d.id for d in line.decisions]
        if proforma.status == DRAFT:  # en un borrador solo existen registros `carried`, derivados de la versión previa
            DentalProformaLineDecisionModel.objects.filter(line_id=line.id).exclude(pk__in=ids).delete()
        known = set(DentalProformaLineDecisionModel.objects.filter(line_id=line.id).values_list('id', flat=True))
        DentalProformaLineDecisionModel.objects.bulk_create([
            DentalProformaLineDecisionModel(
                id=d.id, company_id=self.company_id, line_id=line.id, kind=d.kind, decision=d.decision,
                decided_at=d.decided_at, recorded_by=d.recorded_by, recorded_by_name=d.recorded_by_name,
                accepted_by_name=d.accepted_by_name, medium=d.medium, reference=d.reference, reason=d.reason,
                batch_key=d.batch_key, source_decision_id=d.source_decision_id)
            for d in line.decisions if d.id not in known])
