"""Puerto neutro para valorar los movimientos de inventario de una empresa con inventario valorado.

Costeo registra el proveedor al arrancar; Inventario lo invoca dentro de la sección crítica de cada movimiento,
de modo que ningún módulo de negocio importa al otro. Sin proveedor, o sin adopción de valoración, no hace nada.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class MovementValue:
    """Valor que aporta quien origina una entrada: costo unitario (compra) o valor total (ajuste positivo)."""

    cost_origin: str
    unit_cost: Decimal | None = None
    total_value: Decimal | None = None
    declared_zero: bool = False


@dataclass(frozen=True)
class MovementToValue:
    movement_id: UUID
    product_id: UUID
    warehouse_id: UUID
    kind: str  # 'in' | 'out'
    quantity: Decimal
    occurred_at: datetime
    source_type: str | None = None
    source_id: str = ''
    reverses_id: UUID | None = None
    value: MovementValue | None = None


class ValuationRejected(Exception):
    """La valoración no se puede aplicar. `code`: `valuation_required` | `valuation_invalid` | `valuation_blocked`."""

    def __init__(self, code: str, message: str, field: str = 'total_value'):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


class Provider(Protocol):
    def is_valued(self, company_id: UUID) -> bool: ...

    def value_movement(self, company_id: UUID, movement: MovementToValue) -> None: ...


_provider: Provider | None = None


def register(provider: Provider | None) -> None:
    global _provider
    _provider = provider


def is_valued(company_id: UUID) -> bool:
    """Verdadero si la empresa adoptó una valoración (inventario valorado)."""
    return _provider is not None and bool(_provider.is_valued(company_id))


def value_movement(company_id: UUID, movement: MovementToValue) -> None:
    """Valora el movimiento (dentro de la transacción del llamador) o lanza `ValuationRejected`."""
    if _provider is not None:
        _provider.value_movement(company_id, movement)
