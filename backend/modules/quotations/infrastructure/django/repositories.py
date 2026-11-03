from datetime import date
from uuid import UUID

from django.db import transaction
from django.db.models import Q

from modules.quotations.domain.proforma import DRAFT, PRESENTED, Proforma, ProformaLine
from modules.quotations.infrastructure.django.models import ProformaCounterModel, ProformaLineModel, ProformaModel


def to_domain(row: ProformaModel) -> Proforma:
    lines = [ProformaLine(l.id, l.service_id, l.description, l.quantity, l.unit_price, l.treatment_item_id, l.piece)
             for l in row.lines.all()]
    return Proforma(row.id, row.number, row.version, row.status, row.customer_id, row.customer_name, row.date,
                    row.valid_until, row.notes, lines, row.created_by)


class DjangoProformaRepository:
    """Toda consulta filtra por la empresa recibida."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _qs(self):
        return ProformaModel.objects.filter(company_id=self.company_id).prefetch_related('lines')

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

    def save(self, proforma: Proforma) -> None:
        with transaction.atomic():
            ProformaModel.objects.update_or_create(
                id=proforma.id, company_id=self.company_id,
                defaults={'number': proforma.number, 'version': proforma.version, 'status': proforma.status,
                          'customer_id': proforma.customer_id, 'customer_name': proforma.customer_name,
                          'date': proforma.date, 'valid_until': proforma.valid_until, 'notes': proforma.notes,
                          'created_by': proforma.created_by})
            ProformaLineModel.objects.filter(proforma_id=proforma.id).delete()
            ProformaLineModel.objects.bulk_create([
                ProformaLineModel(id=l.id, proforma_id=proforma.id, position=i, service_id=l.service_id,
                                  description=l.description, quantity=l.quantity, unit_price=l.unit_price,
                                  treatment_item_id=l.treatment_item_id, piece=l.piece)
                for i, l in enumerate(proforma.lines)])
