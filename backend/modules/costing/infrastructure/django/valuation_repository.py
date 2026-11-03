from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from django.db import IntegrityError, transaction

from modules.costing.domain.costing import CostState, Valuation

from .models import MovementValuationModel, ProductCostModel, ValuationAdoptionModel


@dataclass(frozen=True)
class StoredValuation:
    """Snapshot guardado, con su posición de inserción."""

    id: int
    movement_id: UUID
    product_id: UUID
    valuation: Valuation
    source_type: str | None
    source_id: str
    occurred_at: datetime
    reverses_movement_id: UUID | None


def _stored(model: MovementValuationModel) -> StoredValuation:
    return StoredValuation(
        id=model.id, movement_id=model.movement_id, product_id=model.product_id,
        valuation=Valuation(
            kind=model.kind, quantity=model.quantity, unit_cost=model.unit_cost, value=model.value,
            average_before=model.average_before, average_after=model.average_after,
            quantity_after=model.quantity_after, total_value_after=model.total_value_after,
            cost_origin=model.cost_origin),
        source_type=model.source_type, source_id=model.source_id, occurred_at=model.occurred_at,
        reverses_movement_id=model.reverses_movement_id)


class DjangoValuationStore:
    """Estado corriente y snapshots de una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def cutoff_at(self) -> datetime | None:
        return ValuationAdoptionModel.objects.filter(company_id=self.company_id).values_list(
            'cutoff_at', flat=True).first()

    def lock_state(self, product_id: UUID) -> CostState:
        """Estado del producto con su fila bloqueada hasta el fin de la transacción (se crea en cero si falta)."""
        queryset = ProductCostModel.objects.select_for_update().filter(
            company_id=self.company_id, product_id=product_id)
        model = queryset.first()
        if model is None:
            try:
                with transaction.atomic():
                    ProductCostModel.objects.create(company_id=self.company_id, product_id=product_id)
            except IntegrityError:
                pass
            model = queryset.get()
        return CostState(model.quantity, model.total_value)

    def save_state(self, product_id: UUID, state: CostState) -> None:
        ProductCostModel.objects.filter(company_id=self.company_id, product_id=product_id).update(
            quantity=state.quantity, total_value=state.total_value)

    def last_occurred_at(self, product_id: UUID) -> datetime | None:
        return (MovementValuationModel.objects.filter(company_id=self.company_id, product_id=product_id)
                .order_by('-occurred_at').values_list('occurred_at', flat=True).first())

    def by_movement(self, movement_id: UUID) -> StoredValuation | None:
        model = MovementValuationModel.objects.filter(company_id=self.company_id, movement_id=movement_id).first()
        return _stored(model) if model else None

    def has_later(self, product_id: UUID, after_id: int) -> bool:
        return MovementValuationModel.objects.filter(
            company_id=self.company_id, product_id=product_id, id__gt=after_id).exists()

    def add(self, *, movement_id: UUID, product_id: UUID, valuation: Valuation, source_type: str | None,
            source_id: str, reverses_movement_id: UUID | None, occurred_at: datetime) -> None:
        MovementValuationModel.objects.create(
            movement_id=movement_id, company_id=self.company_id, product_id=product_id, kind=valuation.kind,
            quantity=valuation.quantity, unit_cost=valuation.unit_cost, value=valuation.value,
            average_before=valuation.average_before, average_after=valuation.average_after,
            quantity_after=valuation.quantity_after, total_value_after=valuation.total_value_after,
            cost_origin=valuation.cost_origin, source_type=source_type, source_id=source_id,
            reverses_movement_id=reverses_movement_id, occurred_at=occurred_at)

    # --- Lecturas ---------------------------------------------------------------------------------------------

    def list_valuations(self, *, product_id: UUID | None = None, source_type: str | None = None,
                        source_id: str | None = None, movement_id: UUID | None = None,
                        date_from: date | None = None, date_to: date | None = None):
        queryset = MovementValuationModel.objects.filter(company_id=self.company_id)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if source_type:
            queryset = queryset.filter(source_type=source_type)
        if source_id:
            queryset = queryset.filter(source_id=source_id)
        if movement_id:
            queryset = queryset.filter(movement_id=movement_id)
        if date_from:
            queryset = queryset.filter(occurred_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(occurred_at__date__lte=date_to)
        return queryset.order_by('-occurred_at', '-id')

    def list_costs(self):
        return ProductCostModel.objects.filter(company_id=self.company_id).exclude(quantity=0, total_value=0)
