"""Proveedor de Costeo del puerto `shared.stock_valuation`."""
from uuid import UUID

from modules.costing.application.movement_valuation import ValueMovement
from modules.costing.domain.exceptions import MovementValuationRejected
from shared import stock_valuation

from .django.models import ValuationAdoptionModel
from .django.valuation_repository import DjangoValuationStore


class CostingValuationProvider:
    def is_valued(self, company_id: UUID) -> bool:
        return ValuationAdoptionModel.objects.filter(company_id=company_id).exists()

    def value_movement(self, company_id: UUID, movement: stock_valuation.MovementToValue) -> None:
        try:
            ValueMovement(DjangoValuationStore(company_id)).execute(movement)
        except MovementValuationRejected as exc:
            raise stock_valuation.ValuationRejected(exc.code, exc.message, exc.field) from exc
