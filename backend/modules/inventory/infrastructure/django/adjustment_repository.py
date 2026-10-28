from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from modules.inventory.domain.adjustment import StockAdjustment
from modules.inventory.domain.exceptions import AdjustmentIdReused
from modules.inventory.domain.movement import MovementStatus
from modules.inventory.domain.repositories import AdjustmentFilters

from .models import StockAdjustmentModel


def to_entity(model: StockAdjustmentModel) -> StockAdjustment:
    return StockAdjustment(
        id=model.id, product_id=model.product_id, warehouse_id=model.warehouse_id,
        system_quantity=model.system_quantity, counted_quantity=model.counted_quantity, reason=model.reason,
        user_id=model.user_id, user_name=model.user_name, reference=model.reference,
        movement_id=model.movement_id, created_at=model.created_at, status=MovementStatus(model.movement.status))


class AdjustmentList:
    """Vista perezosa de entidades sobre un queryset (paginable sin cargar todo)."""

    def __init__(self, queryset: QuerySet):
        self._queryset = queryset

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [to_entity(model) for model in self._queryset[index]]
        return to_entity(self._queryset[index])

    def __iter__(self):
        return (to_entity(model) for model in self._queryset)


class DjangoStockAdjustmentRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _adjustments(self) -> QuerySet:
        return StockAdjustmentModel.objects.filter(company_id=self.company_id).select_related('movement')

    def get(self, adjustment_id: UUID) -> StockAdjustment | None:
        model = self._adjustments().filter(pk=adjustment_id).first()
        return to_entity(model) if model else None

    def insert(self, adjustment: StockAdjustment) -> StockAdjustment:
        try:
            with transaction.atomic():
                StockAdjustmentModel.objects.create(
                    id=adjustment.id, company_id=self.company_id, reference=adjustment.reference,
                    product_id=adjustment.product_id, warehouse_id=adjustment.warehouse_id,
                    system_quantity=adjustment.system_quantity, counted_quantity=adjustment.counted_quantity,
                    difference=adjustment.difference, reason=adjustment.reason, user_id=adjustment.user_id,
                    user_name=adjustment.user_name, movement_id=adjustment.movement_id)
        except IntegrityError:
            # La clave (o la referencia derivada de ella) ya existe en otra empresa: se rechaza sin revelar nada
            # y el movimiento ya registrado se revierte con la transacción del caso de uso.
            raise AdjustmentIdReused() from None
        return self.get(adjustment.id)

    def list(self, filters: AdjustmentFilters) -> AdjustmentList:
        queryset = self._adjustments().order_by('-created_at', 'id')
        if filters.date_from:
            queryset = queryset.filter(created_at__date__gte=filters.date_from)
        if filters.date_to:
            queryset = queryset.filter(created_at__date__lte=filters.date_to)
        if filters.product_id:
            queryset = queryset.filter(product_id=filters.product_id)
        if filters.warehouse_id:
            queryset = queryset.filter(warehouse_id=filters.warehouse_id)
        return AdjustmentList(queryset)
