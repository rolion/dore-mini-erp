from dataclasses import dataclass
from datetime import date
from uuid import UUID

from modules.inventory.domain.exceptions import (
    OpeningConflict,
    OpeningIdReused,
    OpeningValidationError,
    StockHistoryExists,
    WarehouseNotFound,
)
from modules.inventory.domain.repositories import StockRepository
from modules.inventory.domain.stock import RegisteredOpening, StockOpening, check_quantity_for_unit

from .ports import ProductCatalog


@dataclass(frozen=True)
class OpeningOutcome:
    registered: RegisteredOpening
    replayed: bool


class RegisterOpening:
    """Registra la apertura de existencias de un almacén (AC-01..03): todo o nada e idempotente por `opening_id`."""

    def __init__(self, stock: StockRepository, products: ProductCatalog):
        self.stock = stock
        self.products = products

    def execute(self, opening_id: UUID, warehouse_id: UUID, movement_date: date, reference: object,
                lines: list[tuple[UUID, object]], today: date, created_by_id: int | None = None) -> OpeningOutcome:
        opening = StockOpening.create(opening_id, warehouse_id, movement_date, reference, lines, today)
        with self.stock.atomic():
            warehouse = self.stock.lock_warehouse(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(warehouse_id)
            existing = self.stock.find_opening(opening_id)
            if existing is not None:
                return self._replay(existing, opening)
            if not warehouse.active:
                raise OpeningValidationError({'warehouse_id': ['El almacén debe estar activo.']})
            self._validate_products(opening)
            self._reject_history(opening)
            try:
                self.stock.save_opening(opening, created_by_id)
            except OpeningConflict:
                # Otra escritura se adelantó pese al bloqueo: se reinterpreta con lo que ya existe.
                existing = self.stock.find_opening(opening_id)
                if existing is not None:
                    return self._replay(existing, opening)
                self._reject_history(opening)
                raise
            registered = self.stock.find_opening(opening_id)
        return OpeningOutcome(registered, replayed=False)

    @staticmethod
    def _replay(existing: RegisteredOpening, opening: StockOpening) -> OpeningOutcome:
        if not existing.opening.same_content_as(opening):
            raise OpeningIdReused()
        return OpeningOutcome(existing, replayed=True)

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

    def __init__(self, stock: StockRepository):
        self.stock = stock

    def execute(self, warehouse_id: UUID, product_ids: list[UUID]) -> list[UUID]:
        found = self.stock.products_with_history(warehouse_id, product_ids)
        return [product_id for product_id in product_ids if product_id in found]
