"""Fachada pública del módulo Inventory para otros módulos (Ventas, Compras, Ajustes).

Es la única vía de entrada entre módulos: recibe `company_id` como primer argumento y devuelve DTO inmutables.
"""
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from modules.inventory.application.lot_use_cases import CreateLot, GetLot, ReleaseLot
from modules.inventory.application.movement_use_cases import (
    GetBalance,
    OutputLine,
    RecordMovement,
    RecordOutputs,
    ReverseMovement,
    ReverseSourceMovements,
)
from modules.inventory.domain.exceptions import (  # noqa: F401  (se reexportan para quien llama a la fachada)
    InsufficientStock,
    LotNotFound,
    LotNumberingRejected,
    MovementConflict,
    MovementNotFound,
    MovementValidationError,
    Shortage,
)
from modules.inventory.domain.lot import LotPosition
from modules.inventory.domain.movement import MovementSource, StockMovement
from modules.inventory.infrastructure.adapters import (
    CatalogProductDirectory,
    LotNumberingAdapter,
    ModularityInventoryPolicy,
)
from modules.inventory.infrastructure.django.lot_repository import DjangoStockLotRepository
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
    lot_id: UUID | None = None


def _record(movement: StockMovement) -> MovementRecord:
    return MovementRecord(
        id=movement.id, product_id=movement.product_id, warehouse_id=movement.warehouse_id,
        kind=movement.kind.value, quantity=movement.quantity, status=movement.status.value,
        reverses_id=movement.reverses_id, occurred_at=movement.occurred_at, reference=movement.reference,
        user_name=movement.user_name, lot_id=movement.lot_id)


def record_movement(company_id: UUID, *, product_id: UUID, warehouse_id: UUID, kind: str, quantity: Decimal,
                    user_id: UUID | None, user_name: str, reference: str = '', reason: str = '',
                    source_type: str | None = None, source_id: str = '', source_line: str = '',
                    occurred_at: datetime | None = None,
                    lot_id: UUID | None = None) -> tuple[MovementRecord, bool]:
    """Registra una entrada (`in`) o salida (`out`); devuelve `(movimiento, creado)`.

    Sin `lot_id` una salida solo consume el stock sin lote. Con `lot_id` (empaque) la salida exige un lote liberado
    con saldo suficiente: `MovementConflict('lot_not_released')` o `InsufficientStock`. Las entradas a un lote se crean
    con `create_lot`.

    Es idempotente por operación de origen: repetir la misma `(source_type, source_id, source_line)` con el mismo
    producto, almacén y tipo devuelve el movimiento existente con `creado=False`.
    """
    source = MovementSource(source_type, source_id, source_line) if source_type else None
    use_case = RecordMovement(
        DjangoStockMovementRepository(company_id), DjangoWarehouseRepository(company_id),
        CatalogProductDirectory(company_id), ModularityInventoryPolicy(company_id),
        DjangoStockLotRepository(company_id))
    movement, created = use_case.execute(
        product_id=product_id, warehouse_id=warehouse_id, kind=kind, quantity=quantity, user_id=user_id,
        user_name=user_name, reference=reference, reason=reason, source=source, occurred_at=occurred_at,
        lot_id=lot_id)
    return _record(movement), created


def reverse_movement(company_id: UUID, movement_id: UUID, *, user_id: UUID | None, user_name: str,
                     reason: str, manual_only: bool = False) -> MovementRecord:
    """Revierte un movimiento con un contramovimiento; el original queda «revertido». El motivo es obligatorio.

    Con `manual_only` rechaza los movimientos de Ventas y Compras (se corrigen desde su documento).
    """
    counter = ReverseMovement(
        DjangoStockMovementRepository(company_id), ModularityInventoryPolicy(company_id),
        DjangoStockLotRepository(company_id)).execute(
        movement_id, user_id=user_id, user_name=user_name, reason=reason, manual_only=manual_only)
    return _record(counter)


def reverse_source_movements(company_id: UUID, source_type: str, source_id: str, *, user_id: UUID | None,
                             user_name: str, reason: str) -> list[MovementRecord]:
    """Revierte todos los movimientos confirmados de un documento de origen: todos o ninguno.

    Aplica la política de stock negativo al conjunto; con saldo insuficiente lanza `InsufficientStock` con todas las
    líneas faltantes sin cambiar nada. Sin movimientos confirmados pendientes devuelve `[]`.
    """
    counters = ReverseSourceMovements(
        DjangoStockMovementRepository(company_id), ModularityInventoryPolicy(company_id),
        DjangoStockLotRepository(company_id)).execute(
        source_type, source_id, user_id=user_id, user_name=user_name, reason=reason)
    return [_record(c) for c in counters]


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
    status: str = 'confirmed'
    reversed_by_id: UUID | None = None
    reversed_by_reference: str = ''


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
    """Almacenes activos de la empresa por nombre. Solo lectura: no siembra el predeterminado."""
    return [WarehouseInfo(w.id, w.name, w.is_default)
            for w in DjangoWarehouseRepository(company_id).list(active=True)]


def get_warehouse_names(company_id: UUID, warehouse_ids) -> dict[UUID, str]:
    """Nombre de cada almacén indicado de la empresa, activo o no (los ids de otra empresa no aparecen)."""
    repository = DjangoWarehouseRepository(company_id)
    found = {warehouse_id: repository.get(warehouse_id) for warehouse_id in set(warehouse_ids)}
    return {warehouse_id: warehouse.name for warehouse_id, warehouse in found.items() if warehouse is not None}


def get_stock_products(company_id: UUID, product_ids) -> dict[UUID, StockProduct]:
    """De los productos indicados, solo los de la empresa que controlan stock."""
    found = CatalogProductDirectory(company_id).get_products(product_ids)
    return {pid: StockProduct(p.id, p.name, p.unit_abbreviation, p.allows_fractions)
            for pid, p in found.items() if p.tracks_stock}


def get_balances(company_id: UUID, warehouse_id: UUID, product_ids, *, unlotted: bool = False) -> dict[UUID, Decimal]:
    """Existencia de cada producto en el almacén (0 sin movimientos), en una consulta.

    Con `unlotted` solo cuenta el stock sin lote: lo único que puede consumir una salida sin lote (una venta). El
    físico de los lotes (también el de los liberados) se gasta indicando el lote, y el de los lotes en refrigeración
    está bloqueado.
    """
    return DjangoStockMovementRepository(company_id).balances_for(warehouse_id, list(product_ids), unlotted=unlotted)


def list_movements_for_source(company_id: UUID, source_type: str, source_id: str) -> list[SourceMovement]:
    """Movimientos de un documento de origen, con producto, unidad y almacén ya nombrados."""
    repository = DjangoStockMovementRepository(company_id)
    movements = repository.find_by_source_id(source_type, source_id)
    if not movements:
        return []
    counters = repository.counters_of([m.id for m in movements])
    products = CatalogProductDirectory(company_id).get_products({m.product_id for m in movements})
    warehouses = {w.id: w.name for w in DjangoWarehouseRepository(company_id).list()}
    return [SourceMovement(
        id=m.id, product_id=m.product_id, product_name=products[m.product_id].name if m.product_id in products else '',
        unit_abbreviation=products[m.product_id].unit_abbreviation if m.product_id in products else None,
        warehouse_id=m.warehouse_id, warehouse_name=warehouses.get(m.warehouse_id, ''), quantity=m.quantity,
        occurred_at=m.occurred_at, reference=m.reference, user_name=m.user_name, status=m.status.value,
        reversed_by_id=counters[m.id].id if m.id in counters else None,
        reversed_by_reference=counters[m.id].reference if m.id in counters else '') for m in movements]


# --- Existencias de toda la empresa (Costeo) -------------------------------------------------------------------


@dataclass(frozen=True)
class WarehouseQuantity:
    warehouse_id: UUID
    warehouse_name: str
    quantity: Decimal


@dataclass(frozen=True)
class ProductStock:
    """Existencia de un producto en toda la empresa: total y desglose por almacén (solo almacenes con saldo)."""

    product_id: UUID
    product_name: str
    unit_abbreviation: str | None
    quantity: Decimal
    warehouses: tuple[WarehouseQuantity, ...]


def lock_company_stock(company_id: UUID) -> AbstractContextManager[None]:
    """Transacción que serializa los movimientos de todos los almacenes de la empresa mientras dura."""
    return DjangoStockMovementRepository(company_id).locked_company()


def get_company_stock(company_id: UUID) -> list[ProductStock]:
    """Productos con saldo distinto de cero en algún almacén, con su total y desglose, por nombre."""
    entries = [e for e in DjangoStockMovementRepository(company_id).list_balances()[:] if e.quantity != 0]
    if not entries:
        return []
    products = CatalogProductDirectory(company_id).get_products({e.product_id for e in entries})
    grouped: dict[UUID, list[WarehouseQuantity]] = {}
    for entry in entries:
        grouped.setdefault(entry.product_id, []).append(
            WarehouseQuantity(entry.warehouse_id, entry.warehouse_name, entry.quantity))
    result = []
    for product_id, warehouses in grouped.items():
        info = products.get(product_id)
        result.append(ProductStock(
            product_id=product_id, product_name=info.name if info else '',
            unit_abbreviation=info.unit_abbreviation if info else None,
            quantity=sum((w.quantity for w in warehouses), Decimal('0')), warehouses=tuple(warehouses)))
    return sorted(result, key=lambda p: (p.product_name.lower(), str(p.product_id)))


def get_product_totals(company_id: UUID, product_ids) -> dict[UUID, Decimal]:
    """Saldo total (suma de almacenes) de los productos indicados; los que no tienen movimientos valen cero."""
    wanted = set(product_ids)
    totals = {pid: Decimal('0') for pid in wanted}
    for row in DjangoStockMovementRepository(company_id).list_balances(product_ids=wanted)[:]:
        totals[row.product_id] += row.quantity
    return totals


def get_product_names(company_id: UUID, product_ids) -> dict[UUID, tuple[str, str | None]]:
    """Nombre y unidad base de los productos indicados (para mostrar datos ya registrados por otros módulos)."""
    found = CatalogProductDirectory(company_id).get_products(product_ids)
    return {pid: (p.name, p.unit_abbreviation) for pid, p in found.items()}


# --- Lotes (Producción: crear, liberar y consultar) ----------------------------------------------------------


@dataclass(frozen=True)
class LotRecord:
    """Lote con su saldo físico y su disponible para empaque (solo si está liberado)."""

    id: UUID
    code: str
    product_id: UUID
    warehouse_id: UUID
    warehouse_name: str
    status: str  # 'refrigerating' | 'released'
    lot_date: date
    physical_quantity: Decimal
    available_quantity: Decimal
    fiscal_period_name: str
    created_at: datetime | None = None
    released_at: datetime | None = None
    released_by_name: str = ''


def _lot_record(position: LotPosition) -> LotRecord:
    lot = position.lot
    return LotRecord(
        id=lot.id, code=lot.code, product_id=lot.product_id, warehouse_id=lot.warehouse_id,
        warehouse_name=position.warehouse_name, status=lot.status.value, lot_date=lot.lot_date,
        physical_quantity=position.physical, available_quantity=position.available,
        fiscal_period_name=lot.number.period_name, created_at=lot.created_at, released_at=lot.released_at,
        released_by_name=lot.released_by_name)


def create_lot(company_id: UUID, *, product_id: UUID, warehouse_id: UUID, quantity: Decimal, source_type: str,
               source_id: str, user_id: UUID | None, user_name: str, reference: str = '',
               occurred_at: datetime | None = None) -> tuple[LotRecord, MovementRecord, bool]:
    """Crea un lote **en refrigeración** con su entrada inicial; devuelve `(lote, movimiento, creado)`.

    Una sola transacción: el número `L-YYYYMMDD-NNNN` (correlativo del período fiscal), el lote y la entrada. Es
    idempotente por `(source_type, source_id)`: repetir devuelve el mismo lote con `creado=False`, sin gastar número.
    Sin período fiscal abierto para la fecha lanza `LotNumberingRejected` (`fiscal_period_missing`/`_closed`).
    """
    use_case = CreateLot(
        DjangoStockMovementRepository(company_id), DjangoStockLotRepository(company_id),
        DjangoWarehouseRepository(company_id), CatalogProductDirectory(company_id), LotNumberingAdapter(company_id),
        ModularityInventoryPolicy(company_id))
    result = use_case.execute(
        product_id=product_id, warehouse_id=warehouse_id, quantity=quantity,
        source=MovementSource(source_type, source_id), user_id=user_id, user_name=user_name, reference=reference,
        occurred_at=occurred_at)
    position = DjangoStockLotRepository(company_id).get_position(result.lot.id)
    return _lot_record(position), _record(result.movement), result.created


def release_lot(company_id: UUID, lot_id: UUID, *, user_id: UUID | None,
                user_name: str) -> tuple[LotRecord, bool]:
    """Libera el lote (su stock físico pasa a estar disponible para empaque); devuelve `(lote, cambió)`.

    Idempotente: liberar un lote ya liberado no cambia nada (`cambió=False`). No aplica el tiempo mínimo de
    refrigeración: esa regla es de quien llama (Producción). Lanza `LotNotFound` si el lote no existe.
    """
    position, changed = ReleaseLot(DjangoStockMovementRepository(company_id), DjangoStockLotRepository(company_id)
                                   ).execute(lot_id, user_id=user_id, user_name=user_name)
    return _lot_record(position), changed


def get_lot(company_id: UUID, lot_id: UUID) -> LotRecord:
    """El lote con su físico y disponible vigentes. Lanza `LotNotFound` si no existe en la empresa."""
    return _lot_record(GetLot(DjangoStockLotRepository(company_id)).execute(lot_id))


def list_lots_for_product(company_id: UUID, product_id: UUID, warehouse_id: UUID) -> list[LotRecord]:
    """Lotes del producto en el almacén, del más reciente al más antiguo, con físico y disponible."""
    return [_lot_record(p) for p in DjangoStockLotRepository(company_id).for_product(product_id, warehouse_id)]
