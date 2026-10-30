from dataclasses import dataclass
from decimal import Decimal
from datetime import date, datetime, time
from uuid import UUID

from django.utils import timezone

from modules.inventory.domain.exceptions import (
    OpeningIdReused,
    OpeningValidationError,
    StockHistoryExists,
    StockPositionNotFound,
    WarehouseNotFound,
)
from modules.inventory.domain.movement import MovementKind, MovementSource, StockMovement
from modules.inventory.domain.repositories import StockMovementRepository, WarehouseRepository
from modules.inventory.domain.stock import (
    SOURCE_TYPE,
    BalanceState,
    StockOpening,
    balance_state,
    check_quantity_for_unit,
)

from .movement_ports import ProductDirectory, ProductInfo
from .movement_use_cases import RecordMovement

OPENING_REASON = 'Apertura de existencias'
NOON = time(12, 0)
ZERO = Decimal('0')


@dataclass(frozen=True)
class OpeningOutcome:
    opening: StockOpening
    #: Movimiento de cada producto; las líneas con cantidad 0 no generan movimiento y no aparecen.
    movement_ids: dict[UUID, UUID]
    replayed: bool


def _occurred_at(movement_date: date, today: date) -> datetime:
    """Hoy: el momento actual; otro día: mediodía local de esa fecha (queda dentro del día aunque cambie la zona)."""
    if movement_date == today:
        return timezone.now()
    return timezone.make_aware(datetime.combine(movement_date, NOON))


def _matches(opening: StockOpening, movements: list[StockMovement]) -> bool:
    """Los movimientos ya registrados con esta clave tienen el mismo almacén, fecha, referencia y líneas."""
    first = movements[0]
    stored = (first.warehouse_id, timezone.localtime(first.occurred_at).date(), first.reference,
              frozenset((m.product_id, m.quantity) for m in movements))
    sent = (opening.warehouse_id, opening.movement_date, opening.reference,
            frozenset((line.product_id, line.quantity) for line in opening.recorded_lines))
    return stored == sent


class RegisterOpening:
    """Registra la apertura de existencias de un almacén sobre el libro de movimientos (AC-01..03).

    Una entrada por línea con cantidad > 0, con origen `(inventory_opening, opening_id)`: repetir la clave con el
    mismo contenido devuelve lo ya registrado. Todo o nada: se hace bajo el bloqueo del almacén y en una transacción.
    """

    def __init__(self, stock: StockMovementRepository, warehouses: WarehouseRepository, products: ProductDirectory):
        self.stock = stock
        self.warehouses = warehouses
        self.products = products
        self.recorder = RecordMovement(stock, warehouses, products)

    def execute(self, opening_id: UUID, warehouse_id: UUID, movement_date: date, reference: object,
                lines: list[tuple[UUID, object]], today: date, user_name: str,
                user_id: UUID | None = None) -> OpeningOutcome:
        opening = StockOpening.create(opening_id, warehouse_id, movement_date, reference, lines, today)
        with self.stock.locked(warehouse_id):
            warehouse = self.warehouses.get(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(warehouse_id)
            existing = self.stock.find_by_source_id(SOURCE_TYPE, str(opening_id))
            if existing:
                if not _matches(opening, existing):
                    raise OpeningIdReused()
                return OpeningOutcome(opening, {m.product_id: m.id for m in existing}, replayed=True)
            if not warehouse.active:
                raise OpeningValidationError({'warehouse_id': ['El almacén debe estar activo.']})
            self._validate_products(opening)
            self._reject_history(opening)
            source = MovementSource(SOURCE_TYPE, str(opening_id))
            occurred_at = _occurred_at(movement_date, today)
            movement_ids: dict[UUID, UUID] = {}
            for line in opening.recorded_lines:
                movement, _ = self.recorder.execute(
                    product_id=line.product_id, warehouse_id=warehouse_id, kind=MovementKind.IN,
                    quantity=line.quantity, user_id=user_id, user_name=user_name, reference=opening.reference,
                    reason=OPENING_REASON, source=source, occurred_at=occurred_at)
                movement_ids[line.product_id] = movement.id
            return OpeningOutcome(opening, movement_ids, replayed=False)

    def _validate_products(self, opening: StockOpening) -> None:
        found = self.products.get_products([line.product_id for line in opening.lines])
        line_errors: list[dict[str, list[str]]] = []
        for line in opening.lines:
            product = found.get(line.product_id)
            error: dict[str, list[str]] = {}
            if product is None:
                error['product_id'] = ['El producto no existe.']
            elif not product.tracks_stock:
                error['product_id'] = ['El producto no controla stock.']
            else:
                message = check_quantity_for_unit(line.quantity, product.allows_fractions)
                if message:
                    error['quantity'] = [message]
            line_errors.append(error)
        if any(line_errors):
            raise OpeningValidationError({'lines': line_errors})

    def _reject_history(self, opening: StockOpening) -> None:
        with_history = self.stock.products_with_history(
            opening.warehouse_id, [line.product_id for line in opening.lines])
        if with_history:
            indices = [i for i, line in enumerate(opening.lines) if line.product_id in with_history]
            raise StockHistoryExists(indices, [opening.lines[i].product_id for i in indices])


class CheckOpeningHistory:
    """Productos que ya tienen movimientos en el almacén (para señalar líneas antes de confirmar)."""

    def __init__(self, stock: StockMovementRepository):
        self.stock = stock

    def execute(self, warehouse_id: UUID, product_ids: list[UUID]) -> list[UUID]:
        found = self.stock.products_with_history(warehouse_id, product_ids)
        return [product_id for product_id in product_ids if product_id in found]


@dataclass(frozen=True)
class StockPosition:
    """Existencia de un producto en un almacén, calculada del libro (un par sin movimientos vale 0)."""

    product: ProductInfo
    warehouse_id: UUID
    warehouse_name: str
    warehouse_active: bool
    quantity: Decimal
    has_history: bool = False

    @property
    def state(self) -> BalanceState:
        return balance_state(self.quantity)

    @property
    def can_register_opening(self) -> bool:
        return self.product.active and self.warehouse_active and not self.has_history

    @property
    def can_register_adjustment(self) -> bool:
        return self.warehouse_active


@dataclass(frozen=True)
class StockQuery:
    search: str | None = None
    warehouse_id: UUID | None = None
    #: `True` solo activos, `False` solo inactivos, `None` todos.
    active: bool | None = True
    #: Estado de saldo pedido; `nonzero` = positivo o negativo.
    balance: str | None = None
    #: Categoría del producto; `none` = sin clasificar.
    category: str | None = None
    can_buy: bool | None = None
    can_sell: bool | None = None


class ListStock:
    """Existencias: todos los productos con control de stock por cada almacén, ordenadas por producto y almacén."""

    def __init__(self, stock: StockMovementRepository, warehouses: WarehouseRepository, products: ProductDirectory):
        self.stock = stock
        self.warehouses = warehouses
        self.products = products

    def execute(self, query: StockQuery) -> list[StockPosition]:
        if query.warehouse_id is not None:
            warehouse = self.warehouses.get(query.warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(query.warehouse_id)
            warehouses = [warehouse]
        else:  # sin almacén elegido solo los activos: los inactivos no pueden tener saldo
            warehouses = list(self.warehouses.list(active=True))
        products = self.products.list_stock_products(
            query.search, query.active, category=query.category, can_buy=query.can_buy, can_sell=query.can_sell)
        balances = {(e.product_id, e.warehouse_id): e.quantity for e in self.stock.list_balances()}
        positions = [
            StockPosition(product, warehouse.id, warehouse.name, warehouse.active,
                          balances.get((product.id, warehouse.id), ZERO))
            for product in products for warehouse in sorted(warehouses, key=lambda w: (w.name.lower(), str(w.id)))
        ]
        return [p for p in positions if _matches_balance(p, query.balance)]


def _matches_balance(position: StockPosition, wanted: str | None) -> bool:
    if wanted is None:
        return True
    if wanted == 'nonzero':
        return position.state is not BalanceState.ZERO
    return position.state.value == wanted


class GetStockPosition:
    """Detalle de un par producto/almacén; el producto puede estar inactivo."""

    def __init__(self, stock: StockMovementRepository, warehouses: WarehouseRepository, products: ProductDirectory):
        self.stock = stock
        self.warehouses = warehouses
        self.products = products

    def execute(self, product_id: UUID, warehouse_id: UUID) -> StockPosition:
        product = self.products.get_products([product_id]).get(product_id)
        if product is None or not product.tracks_stock:
            raise StockPositionNotFound(product_id)
        warehouse = self.warehouses.get(warehouse_id)
        if warehouse is None:
            raise WarehouseNotFound(warehouse_id)
        return StockPosition(
            product, warehouse.id, warehouse.name, warehouse.active, self.stock.balance(product_id, warehouse_id),
            has_history=bool(self.stock.products_with_history(warehouse_id, [product_id])))
