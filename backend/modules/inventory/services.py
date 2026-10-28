"""Fachada pública del módulo Inventory para otros módulos (Ventas, Compras, Ajustes).

Es la única vía de entrada entre módulos: recibe `company_id` como primer argumento y devuelve DTO inmutables.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from modules.inventory.application.movement_use_cases import GetBalance, RecordMovement, ReverseMovement
from modules.inventory.domain.exceptions import (  # noqa: F401  (se reexportan para quien llama a la fachada)
    MovementConflict,
    MovementNotFound,
    MovementValidationError,
)
from modules.inventory.domain.movement import MovementSource, StockMovement
from modules.inventory.infrastructure.adapters import CatalogProductDirectory
from modules.inventory.infrastructure.django.movement_repository import DjangoStockMovementRepository
from modules.inventory.infrastructure.django.repositories import DjangoWarehouseRepository


@dataclass(frozen=True)
class MovementRecord:
    id: UUID
    product_id: UUID
    warehouse_id: UUID
    kind: str
    quantity: Decimal
    status: str
    reverses_id: UUID | None


def _record(movement: StockMovement) -> MovementRecord:
    return MovementRecord(
        id=movement.id, product_id=movement.product_id, warehouse_id=movement.warehouse_id,
        kind=movement.kind.value, quantity=movement.quantity, status=movement.status.value,
        reverses_id=movement.reverses_id)


def record_movement(company_id: UUID, *, product_id: UUID, warehouse_id: UUID, kind: str, quantity: Decimal,
                    user_id: UUID | None, user_name: str, reference: str = '', reason: str = '',
                    source_type: str | None = None, source_id: str = '', source_line: str = '',
                    occurred_at: datetime | None = None, allow_negative: bool = False) -> tuple[MovementRecord, bool]:
    """Registra una entrada (`in`) o salida (`out`); devuelve `(movimiento, creado)`.

    Es idempotente por operación de origen: repetir la misma `(source_type, source_id, source_line)` con el mismo
    producto, almacén y tipo devuelve el movimiento existente con `creado=False`.
    """
    source = MovementSource(source_type, source_id, source_line) if source_type else None
    use_case = RecordMovement(
        DjangoStockMovementRepository(company_id), DjangoWarehouseRepository(company_id),
        CatalogProductDirectory(company_id))
    movement, created = use_case.execute(
        product_id=product_id, warehouse_id=warehouse_id, kind=kind, quantity=quantity, user_id=user_id,
        user_name=user_name, reference=reference, reason=reason, source=source, occurred_at=occurred_at,
        allow_negative=allow_negative)
    return _record(movement), created


def reverse_movement(company_id: UUID, movement_id: UUID, *, user_id: UUID | None, user_name: str,
                     reason: str = '', allow_negative: bool = False) -> MovementRecord:
    """Revierte un movimiento con un contramovimiento; el original queda «revertido»."""
    counter = ReverseMovement(DjangoStockMovementRepository(company_id)).execute(
        movement_id, user_id=user_id, user_name=user_name, reason=reason, allow_negative=allow_negative)
    return _record(counter)


def get_balance(company_id: UUID, product_id: UUID, warehouse_id: UUID) -> Decimal:
    """Entradas menos salidas del producto en el almacén."""
    return GetBalance(DjangoStockMovementRepository(company_id)).execute(product_id, warehouse_id)


def has_history(company_id: UUID, product_id: UUID) -> bool:
    """Proveedor del puerto `shared.stock_history`: el producto tiene movimientos."""
    return DjangoStockMovementRepository(company_id).has_history(product_id)
