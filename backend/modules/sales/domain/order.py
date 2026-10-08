from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from shared.domain.money import DECIMALS, MONEY_MAX, NEGATIVE, TOO_LARGE, InvalidMoney, parse_money

from .enums import OrderStatus, PaymentMethod, PaymentStatus, SalesChannel
from .exceptions import OrderItemNotFound, OrderRuleViolation, OrderValidationError

NOTES_MAX_LENGTH = 2000
REASON_MAX_LENGTH = 500
REFERENCE_MAX_LENGTH = 100
QUANTITY_MAX = 100_000

# Marca "no enviado" para ediciones parciales (distinta de `None`, que es un valor válido).
UNSET = object()

ZERO = Decimal('0.00')
OPEN_STATUSES = (OrderStatus.NEW, OrderStatus.IN_PREPARATION, OrderStatus.READY)

# Acciones de estado permitidas por estado (nombres de la API).
_ALLOWED_TRANSITIONS: dict[OrderStatus, tuple[str, ...]] = {
    OrderStatus.NEW: ('prepare', 'cancel'),
    OrderStatus.IN_PREPARATION: ('ready', 'cancel'),
    OrderStatus.READY: ('deliver', 'cancel'),
    OrderStatus.DELIVERED: (),
    OrderStatus.CANCELLED: (),
}

_MONEY_MESSAGES = {
    NEGATIVE: '{label} no puede ser negativo.',
    DECIMALS: '{label} admite como máximo 2 decimales.',
    TOO_LARGE: '{label} no puede superar ' + str(MONEY_MAX) + '.',
}


def _fail(field_name: str, message: str) -> OrderValidationError:
    return OrderValidationError({field_name: [message]})


def _money(value: object, field_name: str, label: str, *, positive: bool = False) -> Decimal:
    try:
        amount = parse_money(value)
    except InvalidMoney as exc:
        message = _MONEY_MESSAGES.get(exc.code, '{label} debe ser un número decimal.')
        raise _fail(field_name, message.format(label=label)) from None
    if positive and amount <= 0:
        raise _fail(field_name, f'{label} debe ser mayor a cero.')
    return amount


def _enum(enum_type: type, value: object, field_name: str, label: str):
    if value is None or value == '':
        raise _fail(field_name, f'{label} es obligatorio.')
    try:
        return enum_type(value)
    except ValueError:
        raise _fail(field_name, f'{label} no es válido.') from None


def _date(value: object, field_name: str, label: str, *, required: bool = True) -> date | None:
    if value is None:
        if required:
            raise _fail(field_name, f'{label} es obligatoria.')
        return None
    if isinstance(value, datetime) or not isinstance(value, date):
        raise _fail(field_name, f'{label} debe ser una fecha válida.')
    return value


def _text(value: object, field_name: str, label: str, max_length: int) -> str:
    if value is None:
        return ''
    if not isinstance(value, str):
        raise _fail(field_name, f'{label} debe ser texto.')
    value = value.strip()
    if len(value) > max_length:
        raise _fail(field_name, f'{label} no puede superar {max_length} caracteres.')
    return value


def validate_quantity(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail('quantity', 'La cantidad debe ser un número entero.')
    if value <= 0:
        raise _fail('quantity', 'La cantidad debe ser mayor a cero.')
    if value > QUANTITY_MAX:
        raise _fail('quantity', f'La cantidad no puede superar {QUANTITY_MAX}.')
    return value


def _check_subtotal_range(subtotal: Decimal) -> None:
    """El subtotal debe caber en un importe válido (la persistencia usa 12 dígitos con 2 decimales)."""
    if subtotal > MONEY_MAX:
        raise _fail('quantity', 'El importe del pedido supera el máximo permitido.')


def _run_checks(checks: list[tuple[str, Callable[[], object]]]) -> tuple[dict[str, object], dict[str, list[str]]]:
    values: dict[str, object] = {}
    errors: dict[str, list[str]] = {}
    for name, check in checks:
        try:
            values[name] = check()
        except OrderValidationError as exc:
            errors.update(exc.errors)
    return values, errors


def _validate_details(sales_channel: object, order_date: object, expected_delivery_date: object,
                      notes: object) -> dict[str, object]:
    """Valida juntos los datos del pedido y devuelve los valores normalizados (errores de todos los campos)."""
    values, errors = _run_checks([
        ('sales_channel', lambda: _enum(SalesChannel, sales_channel, 'sales_channel', 'El canal de venta')),
        ('order_date', lambda: _date(order_date, 'order_date', 'La fecha del pedido')),
        ('expected_delivery_date', lambda: _date(expected_delivery_date, 'expected_delivery_date',
                                                 'La entrega prevista', required=False)),
        ('notes', lambda: _text(notes, 'notes', 'Las notas', NOTES_MAX_LENGTH)),
    ])
    ordered, expected = values.get('order_date'), values.get('expected_delivery_date')
    if ordered and expected and expected < ordered and 'expected_delivery_date' not in errors:
        errors['expected_delivery_date'] = ['La entrega prevista no puede ser anterior a la fecha del pedido.']
    if errors:
        raise OrderValidationError(errors)
    return values


@dataclass
class OrderItem:
    """Línea del pedido con snapshot del nombre y precio del producto al agregarlo."""

    id: UUID
    product_id: UUID
    product_name: str
    unit_price: Decimal
    quantity: int

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Payment:
    id: UUID
    amount: Decimal
    payment_method: PaymentMethod
    payment_date: date
    reference: str = ''
    created_at: datetime | None = None


@dataclass
class Order:
    """Agregado raíz de Sales. Estado, ítems y pagos solo cambian por sus métodos.

    `subtotal`, `total`, `paid_total`, `balance` y `payment_status` se derivan siempre de los ítems, el descuento y
    los pagos: no se asignan desde fuera.
    """

    id: UUID
    sales_channel: SalesChannel
    order_date: date
    customer_id: UUID | None = None
    expected_delivery_date: date | None = None
    delivered_date: date | None = None
    notes: str = ''
    discount: Decimal = ZERO
    status: OrderStatus = OrderStatus.NEW
    cancellation_reason: str = ''
    cancelled_at: datetime | None = None
    items: list[OrderItem] = field(default_factory=list)
    payments: list[Payment] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # --- creación y datos -------------------------------------------------------------------------------------

    @classmethod
    def create(cls, sales_channel: object, order_date: object, customer_id: UUID | None = None,
               expected_delivery_date: object = None, notes: object = '') -> 'Order':
        values = _validate_details(sales_channel, order_date, expected_delivery_date, notes)
        return cls(
            id=uuid4(),
            customer_id=customer_id,
            sales_channel=values['sales_channel'],
            order_date=values['order_date'],
            expected_delivery_date=values['expected_delivery_date'],
            notes=values['notes'],
        )

    def update_details(self, customer_id: object = UNSET, sales_channel: object = UNSET,
                       order_date: object = UNSET, expected_delivery_date: object = UNSET,
                       notes: object = UNSET) -> None:
        self.ensure_editable()
        values = _validate_details(
            self.sales_channel if sales_channel is UNSET else sales_channel,
            self.order_date if order_date is UNSET else order_date,
            self.expected_delivery_date if expected_delivery_date is UNSET else expected_delivery_date,
            self.notes if notes is UNSET else notes,
        )
        if customer_id is not UNSET:
            self.customer_id = customer_id
        self.sales_channel = values['sales_channel']
        self.order_date = values['order_date']
        self.expected_delivery_date = values['expected_delivery_date']
        self.notes = values['notes']

    # --- importes derivados -----------------------------------------------------------------------------------

    @property
    def subtotal(self) -> Decimal:
        return sum((item.subtotal for item in self.items), ZERO)

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount

    @property
    def paid_total(self) -> Decimal:
        return sum((payment.amount for payment in self.payments), ZERO)

    @property
    def balance(self) -> Decimal:
        return self.total - self.paid_total

    @property
    def payment_status(self) -> PaymentStatus:
        if not self.items:
            return PaymentStatus.PENDING
        paid = self.paid_total
        if paid >= self.total:
            return PaymentStatus.PAID
        if paid > 0:
            return PaymentStatus.PARTIAL
        return PaymentStatus.PENDING

    # --- consultas de acciones disponibles --------------------------------------------------------------------

    @property
    def editable(self) -> bool:
        return self.status in OPEN_STATUSES

    @property
    def allowed_transitions(self) -> list[str]:
        return list(_ALLOWED_TRANSITIONS[self.status])

    @property
    def can_register_payment(self) -> bool:
        return self.status is not OrderStatus.CANCELLED and self.balance > 0

    # --- ítems y descuento ------------------------------------------------------------------------------------

    def add_item(self, product_id: UUID, product_name: str, unit_price: Decimal, quantity: object) -> OrderItem:
        self.ensure_editable()
        quantity = validate_quantity(quantity)
        if unit_price <= 0:
            raise _fail('product_id', 'El producto no tiene un precio de venta mayor a cero.')
        if any(item.product_id == product_id for item in self.items):
            raise OrderRuleViolation('duplicate_product',
                                     'El producto ya está en el pedido; modifique su cantidad.')
        _check_subtotal_range(self.subtotal + unit_price * quantity)
        item = OrderItem(id=uuid4(), product_id=product_id, product_name=product_name,
                         unit_price=unit_price, quantity=quantity)
        self.items.append(item)
        return item

    def change_item_quantity(self, item_id: UUID, quantity: object) -> OrderItem:
        self.ensure_editable()
        item = self._find_item(item_id)
        quantity = validate_quantity(quantity)
        new_subtotal = self.subtotal - item.subtotal + item.unit_price * quantity
        _check_subtotal_range(new_subtotal)
        self._check_amounts(new_subtotal)
        item.quantity = quantity
        return item

    def remove_item(self, item_id: UUID) -> None:
        self.ensure_editable()
        item = self._find_item(item_id)
        if self.status is not OrderStatus.NEW and len(self.items) == 1:
            raise OrderRuleViolation('empty_order', 'Un pedido confirmado debe tener al menos un producto.')
        self._check_amounts(self.subtotal - item.subtotal)
        self.items.remove(item)

    def apply_discount(self, discount: object) -> None:
        self.ensure_editable()
        amount = _money(discount, 'discount', 'El descuento')
        if amount > self.subtotal:
            raise _fail('discount', 'El descuento no puede superar el subtotal.')
        if self.subtotal - amount < self.paid_total:
            raise OrderRuleViolation('total_below_paid', 'El total no puede quedar por debajo de lo ya pagado.')
        self.discount = amount

    # --- estados ----------------------------------------------------------------------------------------------

    def start_preparation(self) -> None:
        """Confirma el pedido: NEW -> IN_PREPARATION (exige al menos un ítem)."""
        self._require_status(OrderStatus.NEW)
        if not self.items:
            raise OrderRuleViolation('empty_order', 'El pedido necesita al menos un producto para confirmarse.')
        self.status = OrderStatus.IN_PREPARATION

    def mark_ready(self) -> None:
        self._require_status(OrderStatus.IN_PREPARATION)
        self.status = OrderStatus.READY

    def deliver(self, delivered_date: object, today: date) -> None:
        self._require_status(OrderStatus.READY)
        value = today if delivered_date is None else _date(delivered_date, 'delivered_date', 'La entrega real')
        if value < self.order_date:
            raise _fail('delivered_date', 'La entrega real no puede ser anterior a la fecha del pedido.')
        if value > today:
            raise _fail('delivered_date', 'La entrega real no puede ser futura.')
        self.delivered_date = value
        self.status = OrderStatus.DELIVERED

    def cancel(self, reason: object, now: datetime) -> None:
        if self.status not in OPEN_STATUSES:
            raise self._invalid_transition()
        text = _text(reason, 'reason', 'El motivo de cancelación', REASON_MAX_LENGTH)
        if not text:
            raise _fail('reason', 'El motivo de cancelación es obligatorio.')
        self.cancellation_reason = text
        self.cancelled_at = now
        self.status = OrderStatus.CANCELLED

    # --- pagos ------------------------------------------------------------------------------------------------

    def register_payment(self, amount: object, payment_method: object, payment_date: object, reference: object,
                         today: date) -> Payment:
        if self.status is OrderStatus.CANCELLED:
            raise OrderRuleViolation('order_cancelled', 'El pedido está cancelado: no admite nuevos pagos.')
        values, errors = _run_checks([
            ('amount', lambda: _money(amount, 'amount', 'El monto', positive=True)),
            ('payment_method', lambda: _enum(PaymentMethod, payment_method, 'payment_method', 'El método de pago')),
            ('payment_date', lambda: self._payment_date(payment_date, today)),
            ('reference', lambda: _text(reference, 'reference', 'La referencia', REFERENCE_MAX_LENGTH)),
        ])
        if not errors and values['amount'] > self.balance:
            errors['amount'] = [f'El monto no puede superar el saldo pendiente ({self.balance}).']
        if errors:
            raise OrderValidationError(errors)
        payment = Payment(id=uuid4(), amount=values['amount'], payment_method=values['payment_method'],
                          payment_date=values['payment_date'], reference=values['reference'])
        self.payments.append(payment)
        return payment

    # --- helpers ----------------------------------------------------------------------------------------------

    @staticmethod
    def _payment_date(value: object, today: date) -> date:
        if value is None:
            return today
        parsed = _date(value, 'payment_date', 'La fecha del pago')
        if parsed > today:
            raise _fail('payment_date', 'La fecha del pago no puede ser futura.')
        return parsed

    def ensure_editable(self) -> None:
        if not self.editable:
            raise OrderRuleViolation('order_not_editable', 'El pedido ya no admite cambios.')

    def _require_status(self, expected: OrderStatus) -> None:
        if self.status is not expected:
            raise self._invalid_transition()

    def _invalid_transition(self) -> OrderRuleViolation:
        return OrderRuleViolation('invalid_transition', 'Esa acción no está permitida para el estado actual del pedido.')

    def _find_item(self, item_id: UUID) -> OrderItem:
        for item in self.items:
            if item.id == item_id:
                return item
        raise OrderItemNotFound(item_id)

    def _check_amounts(self, new_subtotal: Decimal) -> None:
        """Comprueba que, con el subtotal propuesto, el descuento y lo pagado siguen siendo coherentes."""
        if self.discount > new_subtotal:
            raise OrderRuleViolation('discount_exceeds_subtotal',
                                     'El descuento superaría el subtotal; ajuste el descuento primero.')
        if new_subtotal - self.discount < self.paid_total:
            raise OrderRuleViolation('total_below_paid', 'El total no puede quedar por debajo de lo ya pagado.')
