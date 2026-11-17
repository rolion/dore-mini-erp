"""Fachada pública de Costeo para otros módulos (única puerta): costo promedio móvil de entradas y salidas.

Todas las funciones corren dentro de la transacción del llamador y filtran por `company_id`.
"""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from django.utils import timezone

from modules.costing.application.cost_use_cases import CostedOutput, CostOutputs, CostReceipt, ReverseReceiptCost
from modules.costing.domain.cost import CostUnavailable
from modules.costing.infrastructure.adapters import InventoryStockTotals
from modules.costing.infrastructure.django.cost_repository import DjangoCostEventRepository
from modules.costing.infrastructure.django.repositories import DjangoAdoptionRepository

__all__ = ['CostUnavailable', 'CostedOutput', 'cost_outputs', 'cost_receipt', 'is_valued', 'reverse_receipt_cost']


def _parts(company_id: UUID):
    return (DjangoCostEventRepository(company_id), DjangoAdoptionRepository(company_id),
            InventoryStockTotals(company_id))


def is_valued(company_id: UUID) -> bool:
    """¿La empresa adoptó la valoración inicial (condición para tener costo)?"""
    return DjangoAdoptionRepository(company_id).get() is not None


def cost_receipt(company_id: UUID, *, source_type: str, source_id: str, lines: list[tuple[UUID, Decimal, Decimal]],
                 occurred_at: datetime | None = None) -> bool:
    """Actualiza el promedio con las líneas `(producto, cantidad, costo unitario)` ya registradas en stock.

    Sin valoración adoptada no hace nada (`False`). No genera asiento. Idempotente por `(origen, producto)`.
    """
    return CostReceipt(*_parts(company_id)).execute(source_type, source_id, lines, occurred_at or timezone.now())


def reverse_receipt_cost(company_id: UUID, *, source_type: str, source_id: str,
                         occurred_at: datetime | None = None) -> None:
    """Registra la reversa de la recepción al costo original, vinculada; el promedio no cambia."""
    ReverseReceiptCost(*_parts(company_id)).execute(source_type, source_id, occurred_at or timezone.now())


def cost_outputs(company_id: UUID, *, source_type: str, source_id: str, lines: list[tuple[UUID, Decimal]],
                 occurred_at: datetime | None = None) -> CostedOutput:
    """Valoriza las salidas `(producto, cantidad)` al promedio vigente, todas o ninguna y de forma idempotente.

    Lanza `CostUnavailable` si no hay valoración adoptada o algún producto no tiene promedio (sin escribir nada).
    """
    return CostOutputs(*_parts(company_id)).execute(source_type, source_id, lines, occurred_at or timezone.now())
