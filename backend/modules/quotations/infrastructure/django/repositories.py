from datetime import date
from uuid import UUID

from django.db import transaction
from django.db.models import Prefetch, Q

from modules.quotations.domain.proforma import DRAFT, PRESENTED, Decision, Proforma, ProformaLine
from modules.quotations.infrastructure.django.models import (
    ProformaCounterModel, ProformaDecisionBatchModel, ProformaLineDecisionModel, ProformaLineModel, ProformaModel,
)


def _decision(row: ProformaLineDecisionModel) -> Decision:
    return Decision(row.id, row.kind, row.decision, row.decided_at, row.recorded_by, row.recorded_by_name,
                    row.accepted_by_name, row.medium, row.reference, row.reason, row.batch_key,
                    row.source_decision_id)


def to_domain(row: ProformaModel) -> Proforma:
    lines = [ProformaLine(l.id, l.service_id, l.description, l.quantity, l.unit_price, l.treatment_item_id, l.piece,
                          l.origin_line_id, l.line_kind, tuple(_decision(d) for d in l.decisions.all()), l.collected)
             for l in row.lines.all()]
    return Proforma(row.id, row.number, row.version, row.status, row.customer_id, row.customer_name, row.date,
                    row.valid_until, row.notes, lines, row.created_by)


class DjangoProformaRepository:
    """Toda consulta filtra por la empresa recibida."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _qs(self):
        return ProformaModel.objects.filter(company_id=self.company_id).prefetch_related(
            Prefetch('lines', queryset=ProformaLineModel.objects.order_by('position').prefetch_related('decisions')))

    def get(self, proforma_id: UUID, *, for_update: bool = False) -> Proforma | None:
        if for_update:  # bloquea solo la cabecera; las líneas se leen después
            if not ProformaModel.objects.select_for_update().filter(
                    company_id=self.company_id, pk=proforma_id).exists():
                return None
        row = self._qs().filter(pk=proforma_id).first()
        return to_domain(row) if row else None

    def search(self, *, customer: str = '', date_from: date | None = None, date_to: date | None = None,
             status: str = ''):
        qs = self._qs()
        if customer:
            qs = qs.filter(Q(customer_name__icontains=customer) | Q(number__icontains=customer))
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if status:
            qs = qs.filter(status=status)
        return qs

    def versions(self, number: str) -> list[Proforma]:
        return [to_domain(r) for r in self._qs().filter(number=number).order_by('version')]

    def origin_lines(self, number: str, version: int) -> dict[UUID, ProformaLine]:
        """Líneas de la versión anterior, por id (vacío en la versión 1)."""
        row = self._qs().filter(number=number, version=version - 1).first()
        return {line.id: line for line in to_domain(row).lines} if row else {}

    def versions_of(self, numbers) -> list[Proforma]:
        return [to_domain(r) for r in self._qs().filter(number__in=list(numbers))]

    def draft_exists(self, number: str) -> bool:
        return ProformaModel.objects.filter(company_id=self.company_id, number=number, status=DRAFT).exists()

    def presented_below(self, number: str, version: int) -> list[Proforma]:
        return [to_domain(r) for r in self._qs().filter(number=number, status=PRESENTED, version__lt=version)]

    def next_number(self) -> str:
        """Consecutivo por empresa; el bloqueo de la fila del contador serializa creaciones concurrentes."""
        ProformaCounterModel.objects.get_or_create(company_id=self.company_id)
        counter = ProformaCounterModel.objects.select_for_update().get(company_id=self.company_id)
        counter.last_number += 1
        counter.save(update_fields=['last_number'])
        return f'PRO-{counter.last_number:06d}'

    # --- idempotencia de decisiones ------------------------------------------------------------------------
    def get_batch(self, key: UUID) -> ProformaDecisionBatchModel | None:
        return ProformaDecisionBatchModel.objects.filter(company_id=self.company_id, idempotency_key=key).first()

    def add_batch(self, key: UUID, proforma_id: UUID, payload_hash: str) -> None:
        ProformaDecisionBatchModel.objects.create(company_id=self.company_id, idempotency_key=key,
                                                  proforma_id=proforma_id, payload_hash=payload_hash)

    def save(self, proforma: Proforma) -> None:
        """Guarda por diferencia: las líneas conservan su id y el libro de decisiones nunca se reescribe."""
        with transaction.atomic():
            ProformaModel.objects.update_or_create(
                id=proforma.id, company_id=self.company_id,
                defaults={'number': proforma.number, 'version': proforma.version, 'status': proforma.status,
                          'customer_id': proforma.customer_id, 'customer_name': proforma.customer_name,
                          'date': proforma.date, 'valid_until': proforma.valid_until, 'notes': proforma.notes,
                          'created_by': proforma.created_by})
            keep = [line.id for line in proforma.lines]
            if proforma.status == DRAFT:  # solo un borrador puede perder líneas
                ProformaLineModel.objects.filter(proforma_id=proforma.id).exclude(pk__in=keep).delete()
            for position, line in enumerate(proforma.lines):
                ProformaLineModel.objects.update_or_create(
                    id=line.id, proforma_id=proforma.id,
                    defaults={'position': position, 'service_id': line.service_id, 'description': line.description,
                              'quantity': line.quantity, 'unit_price': line.unit_price,
                              'treatment_item_id': line.treatment_item_id, 'piece': line.piece,
                              'origin_line_id': line.origin_line_id, 'line_kind': line.line_kind})
                if line.collected:  # monótona: nunca se reinicia desde el dominio
                    ProformaLineModel.objects.filter(pk=line.id).update(collected=True)
                self._save_decisions(proforma, line)

    def _save_decisions(self, proforma: Proforma, line: ProformaLine) -> None:
        ids = [d.id for d in line.decisions]
        if proforma.status == DRAFT:  # en un borrador solo existen registros `carried`, derivados de la versión previa
            ProformaLineDecisionModel.objects.filter(line_id=line.id).exclude(pk__in=ids).delete()
        known = set(ProformaLineDecisionModel.objects.filter(line_id=line.id).values_list('id', flat=True))
        ProformaLineDecisionModel.objects.bulk_create([
            ProformaLineDecisionModel(
                id=d.id, company_id=self.company_id, line_id=line.id, kind=d.kind, decision=d.decision,
                decided_at=d.decided_at, recorded_by=d.recorded_by, recorded_by_name=d.recorded_by_name,
                accepted_by_name=d.accepted_by_name, medium=d.medium, reference=d.reference, reason=d.reason,
                batch_key=d.batch_key, source_decision_id=d.source_decision_id)
            for d in line.decisions if d.id not in known])
