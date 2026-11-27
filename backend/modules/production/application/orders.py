"""Casos de uso de órdenes de producción; leen recetas, Catálogo e Inventario solo por puertos."""
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from modules.production.application.recipes import ProductCatalog
from modules.production.domain.packing import Packing, ProductRef
from modules.production.domain.production_order import (
    OrderIngredient, OrderNotFound, OrderStateError, OrderStatus, OrderValidationError, ProductionOrder,
    parse_preparations)
from modules.production.domain.recipe import Recipe


@dataclass(frozen=True)
class WarehouseView:
    id: UUID
    name: str
    is_default: bool


class WarehouseDirectory(Protocol):
    def active(self) -> list[WarehouseView]: ...
    def names(self, warehouse_ids: Iterable[UUID]) -> dict[UUID, str]: ...


@dataclass(frozen=True)
class Actor:
    user_id: UUID | None
    user_name: str


@dataclass(frozen=True)
class LotView:
    id: UUID
    code: str


class StockGateway(Protocol):
    """Inventario: salidas de ingredientes y entrada del granel con lote. Lanza `InsufficientIngredients`,
    `RefrigerationRejected` u `OrderValidationError`."""

    def consume(self, order: ProductionOrder, lines: list[tuple[UUID, Decimal]], when: datetime,
                actor: Actor) -> None: ...

    def enter_lot(self, order: ProductionOrder, quantity: Decimal, when: datetime, actor: Actor) -> LotView: ...

    def release_lot(self, order: ProductionOrder, actor: Actor) -> None:
        """Libera el lote de la orden en Inventario (idempotente; no crea movimientos)."""

    def pack_out(self, order: ProductionOrder, packing: Packing, when: datetime, actor: Actor) -> None:
        """Salida de los cuñapés del lote y de las bolsas; lanza `InsufficientIngredients` con todos los faltantes."""

    def pack_in(self, packing: Packing, when: datetime, actor: Actor) -> None:
        """Entrada de los packs al stock disponible."""


class CostGateway(Protocol):
    """Costeo opcional: devuelve el costo total consumido (o `None` sin costo) y registra la entrada costeada."""

    def cost_consumption(self, order: ProductionOrder, lines: list[tuple[UUID, Decimal]],
                         when: datetime) -> Decimal | None: ...

    def cost_entry(self, order: ProductionOrder, quantity: Decimal, total_cost: Decimal, when: datetime) -> None: ...


class PackingCostGateway(Protocol):
    def cost_packing_outputs(self, order: ProductionOrder, packing: Packing, when: datetime) -> Decimal | None: ...

    def cost_packing_entry(self, packing: Packing, total_cost: Decimal, when: datetime) -> Decimal: ...


class PackingRepository(Protocol):
    def find(self, order_id: UUID, request_id: UUID) -> Packing | None: ...
    def add(self, packing: Packing) -> Packing: ...


class ReleasePolicy(Protocol):
    """Mínimo de horas de refrigeración de la empresa (ajuste de Modularidad)."""

    def min_refrigeration_hours(self) -> int: ...


class RecipeSource(Protocol):
    def get(self, recipe_id: UUID, *, for_update: bool = False) -> Recipe | None: ...


class OrderRepository(Protocol):
    def get(self, order_id: UUID, *, for_update: bool = False) -> ProductionOrder | None: ...
    def save(self, order: ProductionOrder) -> ProductionOrder: ...
    def list(self, *, status: str = 'all'): ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductionOrders:
    def __init__(self, repository: OrderRepository, recipes: RecipeSource, catalog: ProductCatalog,
                 warehouses: WarehouseDirectory, clock: Callable[[], datetime] = _utc_now,
                 stock: StockGateway | None = None, costs: CostGateway | None = None,
                 policy: ReleasePolicy | None = None, packings: PackingRepository | None = None):
        self.packings = packings
        self.policy = policy
        self.stock = stock
        self.costs = costs
        self.repository = repository
        self.recipes = recipes
        self.catalog = catalog
        self.warehouses = warehouses
        self.clock = clock

    def get(self, order_id: UUID, *, for_update: bool = False) -> ProductionOrder:
        order = self.repository.get(order_id, for_update=for_update)
        if order is None:
            raise OrderNotFound
        return order

    def _warehouse_error(self, warehouse_id: UUID) -> list[str] | None:
        if warehouse_id not in {w.id for w in self.warehouses.active()}:
            return ['El almacén no existe o está inactivo.']
        return None

    def create(self, *, recipe_id: UUID, warehouse_id: UUID, preparations: object) -> ProductionOrder:
        errors: dict = {}
        try:
            parse_preparations(preparations)
        except ValueError as exc:
            errors['preparations'] = [str(exc)]
        recipe = self.recipes.get(recipe_id)
        if recipe is None:
            errors['recipe_id'] = ['La receta no existe.']
        elif not recipe.active:
            errors['recipe_id'] = ['La receta está inactiva.']
        message = self._warehouse_error(warehouse_id)
        if message:
            errors['warehouse_id'] = message
        if errors:
            raise OrderValidationError(errors)
        ids = {recipe.result_product_id, *(line.product_id for line in recipe.ingredients)}
        products = self.catalog.products(ids)
        result = products.get(recipe.result_product_id)
        if result is None or any(line.product_id not in products for line in recipe.ingredients):
            raise OrderValidationError({'recipe_id': ['La receta usa productos que ya no existen.']})
        order = ProductionOrder.create(
            recipe_id=recipe.id, recipe_name=recipe.name, result_product_id=result.id,
            result_product_name=result.name, result_unit_id=result.unit_id,
            result_unit_abbreviation=result.unit_abbreviation, yield_per_preparation=recipe.yield_quantity,
            warehouse_id=warehouse_id, preparations=preparations,
            ingredients=[OrderIngredient(line.product_id, products[line.product_id].name, line.unit_id,
                                         products[line.product_id].unit_abbreviation, line.quantity)
                         for line in recipe.ingredients])
        return self.repository.save(order)

    def update(self, order_id: UUID, *, warehouse_id: UUID, preparations: object) -> ProductionOrder:
        order = self.get(order_id, for_update=True)
        errors: dict = {}
        message = self._warehouse_error(warehouse_id)
        if message:
            errors['warehouse_id'] = message
        try:
            order.change_plan(warehouse_id=warehouse_id, preparations=preparations)
        except OrderValidationError as exc:
            errors.update(exc.errors)
        if errors:
            raise OrderValidationError(errors)
        return self.repository.save(order)

    def start(self, order_id: UUID) -> ProductionOrder:
        order = self.get(order_id, for_update=True)
        message = self._warehouse_error(order.warehouse_id)
        if message and order.status == 'draft':
            raise OrderValidationError({'warehouse_id': message})
        order.start(self.clock())
        return self.repository.save(order)

    def refrigerate(self, order_id: UUID, *, entered_at: object, actual_output: object, ingredients: object,
                    actor: Actor) -> ProductionOrder:
        """Pasa la orden a refrigeración: consume, ingresa el lote con su costo y cambia el estado (todo o nada).

        Debe correr dentro de una transacción: con la orden bloqueada, un reintento ve el estado ya cambiado.
        """
        order = self.get(order_id, for_update=True)
        if order.status != OrderStatus.IN_PREPARATION:
            raise OrderStateError('La orden no está en preparación.')
        now = self.clock()
        entered, output, consumption = order.validate_refrigeration(
            entered_at=entered_at, actual_output=actual_output, ingredients=ingredients, now=now)
        lines = [(line.product_id, consumption[line.product_id]) for line in order.ingredients
                 if consumption[line.product_id] > 0]
        if lines:
            self.stock.consume(order, lines, entered, actor)
        total = self.costs.cost_consumption(order, lines, entered) if lines and self.costs else None
        lot = self.stock.enter_lot(order, output, entered, actor)
        if total is not None:
            self.costs.cost_entry(order, output, total, entered)
        order.refrigerate(now=now, entered_at=entered, actual_output=output, consumption=consumption,
                          lot_id=lot.id, lot_code=lot.code, cost_total=total)
        return self.repository.save(order)

    def min_refrigeration_hours(self) -> int:
        return self.policy.min_refrigeration_hours()

    def release(self, order_id: UUID, *, actor: Actor) -> ProductionOrder:
        """Libera el lote tras el mínimo: orden `ready_to_pack` y lote disponible (todo o nada, idempotente).

        Debe correr dentro de una transacción: con la orden bloqueada, un reintento ve el estado ya cambiado.
        """
        order = self.get(order_id, for_update=True)
        if order.status == OrderStatus.READY_TO_PACK:
            return order
        changed = order.release(now=self.clock(), min_hours=self.min_refrigeration_hours(),
                                user_id=actor.user_id, user_name=actor.user_name)
        if not changed:
            return order
        self.stock.release_lot(order, actor)
        return self.repository.save(order)

    def pack(self, order_id: UUID, *, request_id: UUID, packs: object, pack_product_id: UUID,
             bag_product_id: UUID, actor: Actor) -> tuple[Packing, bool]:
        """Registra una tanda de packs de 6 (salidas, entrada, costo y registro; todo o nada).

        Devuelve `(empaque, creado)`.

        Debe correr dentro de una transacción: con la orden bloqueada, un reintento con el mismo `request_id`
        devuelve el empaque ya registrado sin nuevos movimientos.
        """
        order = self.get(order_id, for_update=True)
        existing = self.packings.find(order.id, request_id)
        if existing is not None:
            return existing, False
        if order.status != OrderStatus.READY_TO_PACK:
            raise OrderStateError('La orden no está lista para empacar.')
        found = self.catalog.products({pack_product_id, bag_product_id})

        def ref(product_id: UUID) -> ProductRef | None:
            info = found.get(product_id)
            return ProductRef(info.id, info.name) if info is not None and info.active else None

        packing = Packing.create(order, request_id=request_id, packs=packs, pack=ref(pack_product_id),
                                 bag=ref(bag_product_id), user_id=actor.user_id, user_name=actor.user_name)
        now = self.clock()
        self.stock.pack_out(order, packing, now, actor)
        total = self.costs.cost_packing_outputs(order, packing, now) if self.costs else None
        self.stock.pack_in(packing, now, actor)
        unit_cost = self.costs.cost_packing_entry(packing, total, now) if total is not None else None
        packing.record_cost(total, unit_cost)
        return self.packings.add(packing), True
