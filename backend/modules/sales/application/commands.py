from datetime import date
from uuid import UUID

from modules.sales.domain.exceptions import OrderNotFound, OrderRuleViolation, OrderValidationError
from modules.sales.domain.order import UNSET, Order, validate_quantity
from modules.sales.domain.repositories import OrderRepository

from .delivery import controlled_lines
from .ports import Actor, Clock, CustomerDirectory, ProductCatalog, SalesSettingsReader, StockOutput


def _load_for_update(repository: OrderRepository, order_id: UUID) -> Order:
    order = repository.get_for_update(order_id)
    if order is None:
        raise OrderNotFound(order_id)
    return order


def _customer_errors(customers: CustomerDirectory, customer_id: UUID) -> dict[str, list[str]]:
    if not customers.is_available():
        return {'customer_id': ['El módulo Clientes no está habilitado.']}
    customer = customers.get_customer_for_sale(customer_id)
    if customer is None:
        return {'customer_id': ['El cliente no existe.']}
    if not customer.active:
        return {'customer_id': ['El cliente está inactivo y no puede asignarse al pedido.']}
    return {}


class CreateOrder:
    def __init__(self, repository: OrderRepository, customers: CustomerDirectory, clock: Clock):
        self.repository = repository
        self.customers = customers
        self.clock = clock

    def execute(self, sales_channel: object = None, order_date: object = None, customer_id: UUID | None = None,
                expected_delivery_date: object = None, notes: object = '') -> Order:
        errors: dict[str, list[str]] = {}
        order = None
        try:
            order = Order.create(
                sales_channel=sales_channel,
                order_date=self.clock.today() if order_date is None else order_date,
                customer_id=customer_id,
                expected_delivery_date=expected_delivery_date,
                notes=notes,
            )
        except OrderValidationError as exc:
            errors.update(exc.errors)
        if customer_id is not None:
            errors.update(_customer_errors(self.customers, customer_id))
        if errors:
            raise OrderValidationError(errors)
        return self.repository.save(order)


class UpdateOrder:
    """Edición parcial de los datos del pedido; el cliente solo se valida si cambia."""

    def __init__(self, repository: OrderRepository, customers: CustomerDirectory):
        self.repository = repository
        self.customers = customers

    def execute(self, order_id: UUID, customer_id: object = UNSET, sales_channel: object = UNSET,
                order_date: object = UNSET, expected_delivery_date: object = UNSET,
                notes: object = UNSET) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.ensure_editable()
        errors: dict[str, list[str]] = {}
        if customer_id is not UNSET and customer_id is not None and customer_id != order.customer_id:
            errors.update(_customer_errors(self.customers, customer_id))
        try:
            order.update_details(customer_id=customer_id, sales_channel=sales_channel, order_date=order_date,
                                 expected_delivery_date=expected_delivery_date, notes=notes)
        except OrderValidationError as exc:
            errors.update(exc.errors)
        if errors:
            raise OrderValidationError(errors)
        return self.repository.save(order)


class AddOrderItem:
    """Agrega un producto activo con snapshot de nombre y precio vigentes (el precio nunca lo envía el cliente)."""

    def __init__(self, repository: OrderRepository, products: ProductCatalog):
        self.repository = repository
        self.products = products

    def execute(self, order_id: UUID, product_id: UUID, quantity: object) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.ensure_editable()
        errors: dict[str, list[str]] = {}
        product = self.products.get_product_for_sale(product_id)
        if product is None:
            errors['product_id'] = ['El producto no existe.']
        elif not product.active:
            errors['product_id'] = ['El producto está inactivo y no puede agregarse al pedido.']
        elif not product.can_sell:
            errors['product_id'] = ['El producto no se puede vender.']
        try:
            validate_quantity(quantity)
        except OrderValidationError as exc:
            errors.update(exc.errors)
        if errors:
            raise OrderValidationError(errors)
        order.add_item(product.id, product.name, product.sale_price, quantity)
        return self.repository.save(order)


class ChangeOrderItemQuantity:
    def __init__(self, repository: OrderRepository):
        self.repository = repository

    def execute(self, order_id: UUID, item_id: UUID, quantity: object) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.change_item_quantity(item_id, quantity)
        return self.repository.save(order)


class RemoveOrderItem:
    def __init__(self, repository: OrderRepository):
        self.repository = repository

    def execute(self, order_id: UUID, item_id: UUID) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.remove_item(item_id)
        return self.repository.save(order)


class ApplyOrderDiscount:
    def __init__(self, repository: OrderRepository, settings: SalesSettingsReader | None = None):
        self.repository = repository
        self.settings = settings

    def execute(self, order_id: UUID, discount: object) -> Order:
        order = _load_for_update(self.repository, order_id)
        if self.settings is None:
            order.apply_discount(discount)
        else:
            order.apply_discount(discount, self.settings.max_discount_percent())
        return self.repository.save(order)


class StartOrderPreparation:
    """Confirma el pedido (NEW -> IN_PREPARATION)."""

    def __init__(self, repository: OrderRepository):
        self.repository = repository

    def execute(self, order_id: UUID) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.start_preparation()
        return self.repository.save(order)


class MarkOrderReady:
    def __init__(self, repository: OrderRepository):
        self.repository = repository

    def execute(self, order_id: UUID) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.mark_ready()
        return self.repository.save(order)


class DeliverOrder:
    """Entrega el pedido (READY -> DELIVERED) y, con Inventario habilitado, registra la salida de sus productos
    controlados en el almacén elegido. Todo ocurre en la transacción de quien llama: si algo falla, no se entrega
    el pedido ni se registra ninguna salida."""

    def __init__(self, repository: OrderRepository, clock: Clock, stock: StockOutput | None = None):
        self.repository = repository
        self.clock = clock
        self.stock = stock

    def execute(self, order_id: UUID, delivered_date: date | None = None, warehouse_id: UUID | None = None,
                actor: Actor | None = None) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.deliver(delivered_date, self.clock.today())
        self._register_outputs(order, warehouse_id, actor)
        return self.repository.save(order)

    def _register_outputs(self, order: Order, warehouse_id: UUID | None, actor: Actor | None) -> None:
        if self.stock is None or not self.stock.is_available():
            return
        planned = controlled_lines(order, self.stock)
        if not planned:
            return
        if not self.stock.active_warehouses():
            raise OrderRuleViolation(
                'no_active_warehouse',
                'No hay un almacén activo para registrar la salida: crea o activa uno en Inventario.')
        if warehouse_id is None:
            raise OrderValidationError({'warehouse_id': ['Elige el almacén de salida.']})
        self.stock.register_outputs(
            warehouse_id, [(product.id, quantity) for product, quantity in planned], order.id, order.code,
            actor or Actor(None, ''))


class CancelOrder:
    def __init__(self, repository: OrderRepository, clock: Clock):
        self.repository = repository
        self.clock = clock

    def execute(self, order_id: UUID, reason: object = None) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.cancel(reason, self.clock.now())
        return self.repository.save(order)


class RegisterPayment:
    def __init__(self, repository: OrderRepository, clock: Clock):
        self.repository = repository
        self.clock = clock

    def execute(self, order_id: UUID, amount: object = None, payment_method: object = None, payment_date: object = None,
                reference: object = '') -> Order:
        order = _load_for_update(self.repository, order_id)
        order.register_payment(amount, payment_method, payment_date, reference, self.clock.today())
        return self.repository.save(order)
