"""Alta de un pedido completo (cabecera, productos, descuento y almacén) ya en preparación, en una sola operación."""
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from modules.sales.domain.exceptions import (
    InsufficientStockForDelivery,
    OrderRuleViolation,
    OrderValidationError,
    ShortLine,
)
from modules.sales.domain.order import Order, validate_quantity
from modules.sales.domain.repositories import OrderRepository

from .commands import _customer_errors
from .delivery import controlled_lines
from .ports import Clock, CustomerDirectory, OrderNumbering, ProductCatalog, SalesSettingsReader, StockOutput

ITEMS_REQUIRED = 'Agregue al menos un producto.'
WAREHOUSE_INVALID = 'El almacén no existe o está inactivo.'
WAREHOUSE_REQUIRED = 'Elija el almacén de salida.'
INSUFFICIENT_MESSAGE = 'No hay existencia suficiente en el almacén elegido.'


@dataclass(frozen=True)
class PlacedItem:
    product_id: UUID
    quantity: object


class PlaceOrder:
    """Crea el pedido con sus productos y descuento y lo deja en IN_PREPARATION (INV-06: todo o nada, dentro de la
    transacción de quien llama). Con Inventario habilitado y productos que controlan stock exige un almacén activo y
    valida la existencia en él (sin reservarla); la entrega vuelve a validarla."""

    def __init__(self, repository: OrderRepository, customers: CustomerDirectory, products: ProductCatalog,
                 clock: Clock, numbering: OrderNumbering, settings: SalesSettingsReader | None = None,
                 stock: StockOutput | None = None):
        self.repository = repository
        self.customers = customers
        self.products = products
        self.clock = clock
        self.numbering = numbering
        self.settings = settings
        self.stock = stock

    def execute(self, items: Sequence[dict] | None = None, sales_channel: object = None, order_date: object = None,
                customer_id: UUID | None = None, expected_delivery_date: object = None, notes: object = '',
                warehouse_id: UUID | None = None, discount: object = None) -> Order:
        errors: dict[str, list[str]] = {}
        order = self._create(errors, sales_channel, order_date, customer_id, expected_delivery_date, notes)
        if customer_id is not None:
            errors.update(_customer_errors(self.customers, customer_id))
        lines = self._valid_lines(items or [], errors)
        if errors:
            raise OrderValidationError(errors)
        self._add_items(order, lines, errors)
        self._apply_discount(order, discount, errors)
        if errors:
            raise OrderValidationError(errors)
        self._assign_warehouse(order, warehouse_id)
        order.ensure_confirmable()
        order.start_preparation(self.numbering.next_number(order.order_date))
        return self.repository.save(order)

    def _create(self, errors, sales_channel, order_date, customer_id, expected_delivery_date, notes) -> Order | None:
        try:
            return Order.create(
                sales_channel=sales_channel,
                order_date=self.clock.today() if order_date is None else order_date,
                customer_id=customer_id, expected_delivery_date=expected_delivery_date, notes=notes)
        except OrderValidationError as exc:
            errors.update(exc.errors)
            return None

    def _valid_lines(self, items: Sequence[dict], errors: dict[str, list[str]]) -> list[tuple]:
        """Valida cada línea (producto activo y vendible, cantidad entera, sin repetir); devuelve (producto, cant.)."""
        if not items:
            errors['items'] = [ITEMS_REQUIRED]
            return []
        messages: list[str] = []
        lines: list[tuple] = []
        seen: set[UUID] = set()
        for number, raw in enumerate(items, start=1):
            product_id, quantity = raw['product_id'], raw['quantity']
            product = self.products.get_product_for_sale(product_id)
            problem = None
            if product is None:
                problem = 'El producto no existe.'
            elif not product.active:
                problem = f'«{product.name}» está inactivo y no puede agregarse al pedido.'
            elif not product.can_sell:
                problem = f'«{product.name}» no se puede vender.'
            elif product_id in seen:
                problem = f'«{product.name}» está repetido; indique una sola línea por producto.'
            else:
                try:
                    validate_quantity(quantity)
                except OrderValidationError as exc:
                    problem = ' '.join(exc.errors['quantity'])
            if problem:
                messages.append(f'Línea {number}: {problem}')
            else:
                seen.add(product_id)
                lines.append((product, quantity))
        if messages:
            errors['items'] = messages
        return lines

    @staticmethod
    def _add_items(order: Order, lines: list[tuple], errors: dict[str, list[str]]) -> None:
        for product, quantity in lines:
            try:
                order.add_item(product.id, product.name, product.sale_price, quantity)
            except OrderValidationError as exc:
                errors.setdefault('items', []).extend(m for messages in exc.errors.values() for m in messages)
                return

    def _apply_discount(self, order: Order, discount: object, errors: dict[str, list[str]]) -> None:
        if errors:
            return
        amount = Decimal('0') if discount is None else discount
        try:
            if self.settings is None:
                order.apply_discount(amount)
            else:
                order.apply_discount(amount, self.settings.max_discount_percent())
        except OrderValidationError as exc:
            errors.update(exc.errors)

    def _assign_warehouse(self, order: Order, warehouse_id: UUID | None) -> None:
        """Con Inventario: valida el almacén y la existencia de los productos controlados; sin él, no guarda almacén."""
        if self.stock is None or not self.stock.is_available():
            order.assign_warehouse(None)
            return
        planned = controlled_lines(order, self.stock)
        warehouses = self.stock.active_warehouses()
        if warehouse_id is not None and all(w.id != warehouse_id for w in warehouses):
            raise OrderValidationError({'warehouse_id': [WAREHOUSE_INVALID]})
        if planned and not warehouses:
            raise OrderRuleViolation(
                'no_active_warehouse',
                'No hay un almacén activo para atender el pedido: crea o activa uno en Inventario.')
        if planned and warehouse_id is None:
            raise OrderValidationError({'warehouse_id': [WAREHOUSE_REQUIRED]})
        if planned and not self.stock.allow_negative_stock():
            self._ensure_stock(warehouses, warehouse_id, planned)
        order.assign_warehouse(warehouse_id)

    def _ensure_stock(self, warehouses, warehouse_id: UUID, planned: list[tuple]) -> None:
        balances = self.stock.balances(warehouse_id, [product.id for product, _ in planned])
        short = [ShortLine(product.id, product.name, product.unit, quantity, balances.get(product.id, Decimal('0')))
                 for product, quantity in planned if balances.get(product.id, Decimal('0')) < quantity]
        if short:
            name = next((w.name for w in warehouses if w.id == warehouse_id), '')
            raise InsufficientStockForDelivery(INSUFFICIENT_MESSAGE, warehouse_id, name, short)
