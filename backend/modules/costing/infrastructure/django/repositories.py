from uuid import UUID

from django.db import IntegrityError, transaction

from modules.costing.domain.exceptions import ValuationAlreadyAdopted
from modules.costing.domain.valuation import ValuationAdoption, ValuationLine

from .models import ValuationAdoptionModel, ValuationLineModel


class DjangoAdoptionRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get(self) -> ValuationAdoption | None:
        model = ValuationAdoptionModel.objects.filter(company_id=self.company_id).first()
        if model is None:
            return None
        lines = ValuationLineModel.objects.filter(company_id=self.company_id, adoption_id=model.id)
        return ValuationAdoption(
            id=model.id, cutoff_at=model.cutoff_at, method=model.method, user_id=model.user_id,
            user_name=model.user_name,
            lines=tuple(ValuationLine(
                product_id=line.product_id, reconciled_quantity=line.reconciled_quantity,
                total_value=line.total_value, unit_cost=line.unit_cost, declared_zero=line.declared_zero,
                source=line.source) for line in sorted(lines, key=lambda l: str(l.product_id))))

    def save(self, adoption: ValuationAdoption) -> None:
        try:
            with transaction.atomic():
                ValuationAdoptionModel.objects.create(
                    id=adoption.id, company_id=self.company_id, cutoff_at=adoption.cutoff_at,
                    method=adoption.method, user_id=adoption.user_id, user_name=adoption.user_name)
                ValuationLineModel.objects.bulk_create([ValuationLineModel(
                    adoption_id=adoption.id, company_id=self.company_id, product_id=line.product_id,
                    reconciled_quantity=line.reconciled_quantity, total_value=line.total_value,
                    unit_cost=line.unit_cost, declared_zero=line.declared_zero, source=line.source)
                    for line in adoption.lines])
        except IntegrityError:  # carrera: la restricción de una adopción por empresa manda
            raise ValuationAlreadyAdopted() from None
