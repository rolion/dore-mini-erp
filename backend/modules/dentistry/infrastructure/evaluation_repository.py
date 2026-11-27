from django.db.models import Max
from django.utils import timezone

from modules.dentistry.domain.odontogram import (
    DRAFT, Evaluation, EvaluationNotFound, Finding, GeneralFinding,
)
from .evaluation_models import EvaluationFindingModel, EvaluationGeneralFindingModel, EvaluationModel


def to_domain(row: EvaluationModel) -> Evaluation:
    return Evaluation(
        row.customer_id, row.dentition, row.clinical_date, sequence=row.sequence, status=row.status,
        professional_id=row.professional_id,
        findings=[Finding(f.piece, f.condition, tuple(f.surfaces), f.diagnosis, f.notes, f.id)
                  for f in row.findings.all()],
        general_findings=[GeneralFinding(g.diagnosis, g.notes, g.id) for g in row.general_findings.all()],
        amends_id=row.amends_id, amendment_reason=row.amendment_reason, catalog_version=row.catalog_version,
        id=row.id)


class DjangoEvaluationRepository:
    def __init__(self, company_id):
        self.company_id = company_id

    def rows(self):
        return EvaluationModel.objects.filter(company_id=self.company_id)

    def get(self, evaluation_id, *, locked=False) -> EvaluationModel:
        rows = self.rows()
        if locked:
            rows = rows.select_for_update()
        row = rows.filter(id=evaluation_id).first()
        if row is None:
            raise EvaluationNotFound('Evaluación no encontrada.')
        return row

    def for_customer(self, customer_id):
        return self.rows().filter(customer_id=customer_id).select_related('amends')

    def draft_of(self, customer_id) -> EvaluationModel | None:
        return self.rows().filter(customer_id=customer_id, status=DRAFT).first()

    def next_sequence(self, customer_id) -> int:
        last = self.rows().filter(customer_id=customer_id).aggregate(last=Max('sequence'))['last']
        return (last or 0) + 1

    def entity(self, row: EvaluationModel) -> Evaluation:
        return to_domain(EvaluationModel.objects.prefetch_related('findings', 'general_findings').get(pk=row.pk))

    def create(self, evaluation: Evaluation, sequence: int, author_id, author_name,
               encounter_id=None) -> EvaluationModel:
        row = EvaluationModel.objects.create(
            id=evaluation.id, company_id=self.company_id, customer_id=evaluation.customer_id, sequence=sequence,
            status=evaluation.status, dentition=evaluation.dentition, clinical_date=evaluation.clinical_date,
            professional_id=evaluation.professional_id, catalog_version=evaluation.catalog_version,
            amends_id=evaluation.amends_id, amendment_reason=evaluation.amendment_reason,
            created_by=author_id, created_by_name=author_name, encounter_id=encounter_id)
        self._write_children(row, evaluation)
        return row

    def save_content(self, row: EvaluationModel, evaluation: Evaluation) -> None:
        row.dentition, row.clinical_date = evaluation.dentition, evaluation.clinical_date
        row.professional_id, row.catalog_version = evaluation.professional_id, evaluation.catalog_version
        row.save(update_fields=['dentition', 'clinical_date', 'professional_id', 'catalog_version', 'updated_at'])
        row.findings.all().delete()
        row.general_findings.all().delete()
        self._write_children(row, evaluation)

    def save_confirmed(self, row: EvaluationModel, author_id, author_name) -> None:
        row.status, row.confirmed_by, row.confirmed_by_name = 'confirmed', author_id, author_name
        row.confirmed_at = timezone.now()
        row.save(update_fields=['status', 'confirmed_by', 'confirmed_by_name', 'confirmed_at', 'updated_at'])

    @staticmethod
    def delete(row: EvaluationModel) -> None:
        row.delete()

    @staticmethod
    def _write_children(row: EvaluationModel, evaluation: Evaluation) -> None:
        EvaluationFindingModel.objects.bulk_create([
            EvaluationFindingModel(evaluation=row, position=i, piece=f.piece, condition=f.condition,
                                   surfaces=''.join(f.surfaces), diagnosis=f.diagnosis, notes=f.notes)
            for i, f in enumerate(evaluation.findings)])
        EvaluationGeneralFindingModel.objects.bulk_create([
            EvaluationGeneralFindingModel(evaluation=row, position=i, diagnosis=g.diagnosis, notes=g.notes)
            for i, g in enumerate(evaluation.general_findings)])
