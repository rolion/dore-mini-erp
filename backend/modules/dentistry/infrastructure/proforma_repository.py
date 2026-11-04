from uuid import UUID

from django.db import transaction

from modules.dentistry.domain.proforma import (
    DRAFT, PRESENTED, DentalProforma, DentalProformaLine,
)
from modules.dentistry.infrastructure.proforma_models import (
    DentalProformaCounterModel, DentalProformaLineModel, DentalProformaModel,
)


def to_domain(row: DentalProformaModel) -> DentalProforma:
    lines = [DentalProformaLine(l.id, l.service_id, l.description, l.quantity, l.unit_price, l.dental_piece)
             for l in row.lines.all()]
    return DentalProforma(row.id, row.number, row.version, row.status, row.customer_id, row.patient_name, row.date,
                          row.valid_until, row.notes, lines, row.created_by)


class DjangoDentalProformaRepository:
    """Toda consulta filtra por la empresa recibida."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _qs(self):
        return DentalProformaModel.objects.filter(company_id=self.company_id).prefetch_related('lines')

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

    def save(self, proforma: DentalProforma) -> None:
        with transaction.atomic():
            DentalProformaModel.objects.update_or_create(
                id=proforma.id, company_id=self.company_id,
                defaults={'number': proforma.number, 'version': proforma.version, 'status': proforma.status,
                          'customer_id': proforma.customer_id, 'patient_name': proforma.patient_name,
                          'date': proforma.date, 'valid_until': proforma.valid_until, 'notes': proforma.notes,
                          'created_by': proforma.created_by})
            DentalProformaLineModel.objects.filter(proforma_id=proforma.id).delete()
            DentalProformaLineModel.objects.bulk_create([
                DentalProformaLineModel(id=l.id, proforma_id=proforma.id, position=i, service_id=l.service_id,
                                        description=l.description, quantity=l.quantity, unit_price=l.unit_price,
                                        dental_piece=l.dental_piece)
                for i, l in enumerate(proforma.lines)])
