from datetime import date
from uuid import UUID

from modules.sales.domain.exceptions import OrderNotFound, OrderRuleViolation, OrderValidationError
from modules.sales.domain.order import UNSET, Order, payment_digest, validate_quantity
from modules.sales.domain.repositories import OrderRepository

from .delivery import controlled_lines
from .ports import (
    AT_CONFIRM,
    Actor,
    Clock,
    CustomerDirectory,
    DeliveryCosting,
    ProductCatalog,
    SalesPosting,
    SalesSettingsReader,
    StockOutput,
)


def _load_for_update(repository: OrderRepository, order_id: UUID) -> Order:
    order = repository.get_for_update(order_id)
    if order is None:
        raise OrderNotFound(order_id)
    return order


TOTAL_LOCKED_MESSAGE = ('El pedido ya está contabilizado: no se pueden cambiar sus productos, cantidades ni descuento '
                        'porque alterarían el total.')


def _ensure_total_unlocked(posting: SalesPosting | None, order: Order) -> None:
    """Con el pedido confirmado y cubierto por Contabilidad el total no puede cambiar (regla comercial estable)."""
    if posting is not None and posting.locks_total(order):
        raise OrderRuleViolation('order_total_locked', TOTAL_LOCKED_MESSAGE)


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

    def __init__(self, repository: OrderRepository, products: ProductCatalog, posting: SalesPosting | None = None):
        self.repository = repository
        self.products = products
        self.posting = posting

    def execute(self, order_id: UUID, product_id: UUID, quantity: object) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.ensure_editable()
        _ensure_total_unlocked(self.posting, order)
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
    def __init__(self, repository: OrderRepository, posting: SalesPosting | None = None):
        self.repository = repository
        self.posting = posting

    def execute(self, order_id: UUID, item_id: UUID, quantity: object) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.ensure_editable()
        _ensure_total_unlocked(self.posting, order)
        order.change_item_quantity(item_id, quantity)
        return self.repository.save(order)


class RemoveOrderItem:
    def __init__(self, repository: OrderRepository, posting: SalesPosting | None = None):
        self.repository = repository
        self.posting = posting

    def execute(self, order_id: UUID, item_id: UUID) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.ensure_editable()
        _ensure_total_unlocked(self.posting, order)
        order.remove_item(item_id)
        return self.repository.save(order)


class ApplyOrderDiscount:
    def __init__(self, repository: OrderRepository, settings: SalesSettingsReader | None = None,
                 posting: SalesPosting | None = None):
        self.repository = repository
        self.settings = settings
        self.posting = posting

    def execute(self, order_id: UUID, discount: object) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.ensure_editable()
        _ensure_total_unlocked(self.posting, order)
        if self.settings is None:
            order.apply_discount(discount)
        else:
            order.apply_discount(discount, self.settings.max_discount_percent())
        return self.repository.save(order)


class StartOrderPreparation:
    """Confirma el pedido (NEW -> IN_PREPARATION). No genera asiento: el ingreso se reconoce al entregar."""

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
    """Entrega el pedido (READY -> DELIVERED), registra la salida de sus productos controlados en el almacén elegido
    (con Inventario habilitado) y, con cobertura de Contabilidad, reconoce el ingreso aplicando los anticipos. Todo
    ocurre en la transacción de quien llama: si algo falla, no se entrega el pedido ni queda salida ni asiento."""

    def __init__(self, repository: OrderRepository, clock: Clock, stock: StockOutput | None = None,
                 posting: SalesPosting | None = None, costing: DeliveryCosting | None = None):
        self.repository = repository
        self.clock = clock
        self.stock = stock
        self.posting = posting
        self.costing = costing

    def execute(self, order_id: UUID, delivered_date: date | None = None, warehouse_id: UUID | None = None,
                actor: Actor | None = None) -> Order:
        order = _load_for_update(self.repository, order_id)
        order.deliver(delivered_date, self.clock.today())
        planned = self._register_outputs(order, warehouse_id, actor)
        if self.posting is not None:
            self.posting.recognize_delivery(order, actor or Actor(None, ''))
        if self.costing is not None and planned:
            self.costing.cost_delivery(order, [(product.id, quantity) for product, quantity in planned],
                                       actor or Actor(None, ''))
        return self.repository.save(order)

    def _register_outputs(self, order: Order, warehouse_id: UUID | None, actor: Actor | None) -> list:
        """Registra las salidas y devuelve las líneas de stock controlado (vacío si no hubo salida)."""
        if self.stock is None or not self.stock.is_available():
            return []
        planned = controlled_lines(order, self.stock)
        if not planned:
            return []
        warehouses = self.stock.active_warehouses()
        if warehouse_id is None and any(w.id == order.warehouse_id for w in warehouses):
            warehouse_id = order.warehouse_id  # almacén guardado (si sigue activo): el predeterminado
        if not warehouses:
            raise OrderRuleViolation(
                'no_active_warehouse',
                'No hay un almacén activo para registrar la salida: crea o activa uno en Inventario.')
        if warehouse_id is None:
            raise OrderValidationError({'warehouse_id': ['Elige el almacén de salida.']})
        self.stock.register_outputs(
            warehouse_id, [(product.id, quantity) for product, quantity in planned], order.id, order.code,
            actor or Actor(None, ''))
        return planned


class CancelOrder:
    """Cancela el pedido antes de entregarlo. Con cobros exige confirmar que el dinero se reembolsó fuera de PocketBiz
    y contrarresta sus asientos; un pedido reconocido al confirmar (lógica anterior) revierte su reconocimiento con las
    cuentas originales; uno sin reconocer se cancela sin asiento. Nunca hubo salida de inventario: el stock no cambia."""

    def __init__(self, repository: OrderRepository, clock: Clock, posting: SalesPosting | None = None):
        self.repository = repository
        self.clock = clock
        self.posting = posting

    def execute(self, order_id: UUID, reason: object = None, actor: Actor | None = None,
                refund_acknowledged: bool = False) -> Order:
        actor = actor or Actor(None, '')
        order = _load_for_update(self.repository, order_id)
        order.cancel(reason, self.clock.now(), actor.user_name, bool(refund_acknowledged))
        if self.posting is not None:
            today = self.clock.today()
            if self.posting.recognition_state(order.id) == AT_CONFIRM:
                self.posting.reverse_recognition(order, order.cancellation_reason, actor, today)
            if order.payments:
                self.posting.reverse_payments(order, order.cancellation_reason, actor, today)
        return self.repository.save(order)


class RegisterPayment:
    """Registra un pago del pedido. Con Contabilidad habilitada lo contabiliza antes de guardar (asiento contra Cuentas
    por cobrar si el pedido está reconocido; libro anterior si es anterior a la cobertura), todo en la transacción de
    quien llama (si algo falla no queda pago, saldo ni asiento). Idempotente por `idempotency_key`: `replayed` indica
    que el intento ya estaba registrado y no se creó nada."""

    def __init__(self, repository: OrderRepository, clock: Clock, posting: SalesPosting | None = None):
        self.repository = repository
        self.clock = clock
        self.posting = posting
        self.replayed = False

    def execute(self, order_id: UUID, amount: object = None, payment_method: object = None, payment_date: object = None,
                reference: object = '', idempotency_key: UUID | None = None, actor: Actor | None = None) -> Order:
        self.replayed = False
        order = _load_for_update(self.repository, order_id)
        digest = payment_digest(amount, payment_method, payment_date, reference)
        if idempotency_key is not None:
            existing = order.find_payment_by_key(idempotency_key)
            if existing is not None:
                if existing.request_digest != digest:
                    raise OrderRuleViolation('idempotency_key_reused', 'La clave de la operación ya se usó con otros datos.')
                self.replayed = True
                return order
        payment = order.register_payment(amount, payment_method, payment_date, reference, self.clock.today(),
                                         idempotency_key, digest)
        if self.posting is not None:
            self.posting.record_payment(order, payment, actor or Actor(None, ''), self.clock.today())
        return self.repository.save(order)
