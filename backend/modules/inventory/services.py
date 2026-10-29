"""Fachada pública del módulo Inventory para otros módulos (Ventas, Compras, Ajustes).

Es la única vía de entrada entre módulos: recibe `company_id` como primer argumento y devuelve DTO inmutables.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from modules.inventory.application.movement_use_cases import (
    GetBalance,
    OutputLine,
    RecordMovement,
    RecordOutputs,
    ReverseMovement,
)
from modules.inventory.domain.exceptions import (  # noqa: F401  (se reexportan para quien llama a la fachada)
    InsufficientStock,
    MovementConflict,
    MovementNotFound,
    MovementValidationError,
    Shortage,
)
from modules.inventory.domain.movement import MovementSource, StockMovement
from modules.inventory.infrastructure.adapters import CatalogProductDirectory, ModularityInventoryPolicy
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
    occurred_at: datetime | None = None
    reference: str = ''
    user_name: str = ''


def _record(movement: StockMovement) -> MovementRecord:
    return MovementRecord(
        id=movement.id, product_id=movement.product_id, warehouse_id=movement.warehouse_id,
        kind=movement.kind.value, quantity=movement.quantity, status=movement.status.value,
        reverses_id=movement.reverses_id, occurred_at=movement.occurred_at, reference=movement.reference,
        user_name=movement.user_name)


def record_movement(company_id: UUID, *, product_id: UUID, warehouse_id: UUID, kind: str, quantity: Decimal,
                    user_id: UUID | None, user_name: str, reference: str = '', reason: str = '',
                    source_type: str | None = None, source_id: str = '', source_line: str = '',
                    occurred_at: datetime | None = None) -> tuple[MovementRecord, bool]:
    """Registra una entrada (`in`) o salida (`out`); devuelve `(movimiento, creado)`.

    Es idempotente por operación de origen: repetir la misma `(source_type, source_id, source_line)` con el mismo
    producto, almacén y tipo devuelve el movimiento existente con `creado=False`.
    """
    source = MovementSource(source_type, source_id, source_line) if source_type else None
    use_case = RecordMovement(
        DjangoStockMovementRepository(company_id), DjangoWarehouseRepository(company_id),
        CatalogProductDirectory(company_id), ModularityInventoryPolicy(company_id))
    movement, created = use_case.execute(
        product_id=product_id, warehouse_id=warehouse_id, kind=kind, quantity=quantity, user_id=user_id,
        user_name=user_name, reference=reference, reason=reason, source=source, occurred_at=occurred_at)
    return _record(movement), created


def reverse_movement(company_id: UUID, movement_id: UUID, *, user_id: UUID | None, user_name: str,
                     reason: str = '') -> MovementRecord:
    """Revierte un movimiento con un contramovimiento; el original queda «revertido»."""
    counter = ReverseMovement(
        DjangoStockMovementRepository(company_id), ModularityInventoryPolicy(company_id)).execute(
        movement_id, user_id=user_id, user_name=user_name, reason=reason)
    return _record(counter)


def get_balance(company_id: UUID, product_id: UUID, warehouse_id: UUID) -> Decimal:
    """Entradas menos salidas del producto en el almacén."""
    return GetBalance(DjangoStockMovementRepository(company_id)).execute(product_id, warehouse_id)


def has_history(company_id: UUID, product_id: UUID) -> bool:
    """Proveedor del puerto `shared.stock_history`: el producto tiene movimientos."""
    return DjangoStockMovementRepository(company_id).has_history(product_id)


# --- Salidas de un documento (Ventas) y lecturas para quien las orquesta -------------------------------------


@dataclass(frozen=True)
class WarehouseInfo:
    id: UUID
    name: str
    is_default: bool


@dataclass(frozen=True)
class StockProduct:
    """Producto que controla stock, con su unidad base."""

    id: UUID
    name: str
    unit_abbreviation: str | None
    allows_fractions: bool


@dataclass(frozen=True)
class SourceMovement:
    """Movimiento de un documento de origen, con los nombres ya resueltos para mostrarlo."""

    id: UUID
    product_id: UUID
    product_name: str
    unit_abbreviation: str | None
    warehouse_id: UUID
    warehouse_name: str
    quantity: Decimal
    occurred_at: datetime
    reference: str
    user_name: str


def record_outputs(company_id: UUID, *, warehouse_id: UUID, lines: list[tuple[UUID, Decimal]], source_type: str,
                   source_id: str, user_id: UUID | None, user_name: str,
                   reference: str = '') -> list[tuple[MovementRecord, bool]]:
    """Registra las salidas de un documento en un almacén: todas o ninguna (una sola sección crítica).

    Cada línea es `(producto, cantidad)`; su identidad de origen es `(source_type, source_id, <producto>)`.
    Aplica la política de stock negativo de la empresa; con saldo insuficiente lanza `InsufficientStock` con todas
    las líneas faltantes (`shortages`) sin registrar nada. Repetir la operación devuelve lo ya registrado.
    """
    use_case = RecordOutputs(
        DjangoStockMovementRepository(company_id), DjangoWarehouseRepository(company_id),
        CatalogProductDirectory(company_id), ModularityInventoryPolicy(company_id))
    results = use_case.execute(
        warehouse_id=warehouse_id, lines=[OutputLine(product_id, quantity, str(product_id))
                                          for product_id, quantity in lines],
        source_type=source_type, source_id=source_id, user_id=user_id, user_name=user_name, reference=reference)
    return [(_record(movement), created) for movement, created in results]


def allow_negative_stock(company_id: UUID) -> bool:
    """Política vigente de la empresa (informativa: las salidas la revalidan bajo bloqueo)."""
    return ModularityInventoryPolicy(company_id).allow_negative_stock()


def list_active_warehouses(company_id: UUID) -> list[WarehouseInfo]:
    """Almacenes activos de la empresa por nombre; siembra el predeterminado si la empresa aún no tiene ninguno."""
    repository = DjangoWarehouseRepository(company_id)
    repository.ensure_default()
    return [WarehouseInfo(w.id, w.name, w.is_default) for w in repository.list(active=True)]


def get_stock_products(company_id: UUID, product_ids) -> dict[UUID, StockProduct]:
    """De los productos indicados, solo los de la empresa que controlan stock."""
    found = CatalogProductDirectory(company_id).get_products(product_ids)
    return {pid: StockProduct(p.id, p.name, p.unit_abbreviation, p.allows_fractions)
            for pid, p in found.items() if p.tracks_stock}


def get_balances(company_id: UUID, warehouse_id: UUID, product_ids) -> dict[UUID, Decimal]:
    """Existencia de cada producto en el almacén (0 sin movimientos), en una consulta."""
    return DjangoStockMovementRepository(company_id).balances_for(warehouse_id, list(product_ids))


def list_movements_for_source(company_id: UUID, source_type: str, source_id: str) -> list[SourceMovement]:
    """Movimientos de un documento de origen, con producto, unidad y almacén ya nombrados."""
    movements = DjangoStockMovementRepository(company_id).find_by_source_id(source_type, source_id)
    if not movements:
        return []
    products = CatalogProductDirectory(company_id).get_products({m.product_id for m in movements})
    warehouses = {w.id: w.name for w in DjangoWarehouseRepository(company_id).list()}
    return [SourceMovement(
        id=m.id, product_id=m.product_id, product_name=products[m.product_id].name if m.product_id in products else '',
        unit_abbreviation=products[m.product_id].unit_abbreviation if m.product_id in products else None,
        warehouse_id=m.warehouse_id, warehouse_name=warehouses.get(m.warehouse_id, ''), quantity=m.quantity,
        occurred_at=m.occurred_at, reference=m.reference, user_name=m.user_name) for m in movements]
