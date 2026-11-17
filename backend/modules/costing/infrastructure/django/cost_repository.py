from decimal import Decimal
from uuid import UUID

from modules.costing.domain.cost import CostEvent, CostKind

from .models import CostEventModel


def _to_entity(model: CostEventModel) -> CostEvent:
    return CostEvent(
        kind=CostKind(model.kind), source_type=model.source_type, source_id=model.source_id,
        product_id=model.product_id, quantity=model.quantity, unit_cost=model.unit_cost,
        total_cost=model.total_cost, average_after=model.average_after, occurred_at=model.occurred_at,
        reverses_id=model.reverses_id, id=model.id)


class DjangoCostEventRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _events(self):
        return CostEventModel.objects.filter(company_id=self.company_id)

    def get(self, kind: CostKind, source_type: str, source_id: str, product_id: UUID) -> CostEvent | None:
        model = self._events().filter(kind=kind.value, source_type=source_type, source_id=source_id,
                                      product_id=product_id).first()
        return _to_entity(model) if model else None

    def list_for_source(self, kind: CostKind, source_type: str, source_id: str) -> list[CostEvent]:
        return [_to_entity(m) for m in self._events().filter(
            kind=kind.value, source_type=source_type, source_id=source_id).order_by('id')]

    def latest_averages(self, product_ids) -> dict[UUID, Decimal]:
        """Último promedio por producto (del último evento de recepción)."""
        found: dict = {}
        rows = (self._events().filter(kind=CostKind.IN.value, product_id__in=list(product_ids))
                .order_by('product_id', '-id').values_list('product_id', 'average_after'))
        for product_id, average in rows:
            found.setdefault(product_id, average)
        return found

    def add(self, event: CostEvent) -> CostEvent:
        model = CostEventModel.objects.create(
            company_id=self.company_id, kind=event.kind.value, source_type=event.source_type,
            source_id=event.source_id, product_id=event.product_id, quantity=event.quantity,
            unit_cost=event.unit_cost, total_cost=event.total_cost, average_after=event.average_after,
            reverses_id=event.reverses_id, occurred_at=event.occurred_at)
        return _to_entity(model)
