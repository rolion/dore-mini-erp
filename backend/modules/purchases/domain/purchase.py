import re
from dataclasses import dataclass, field
from collections.abc import Mapping
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from uuid import UUID, uuid4

from shared.domain.money import DECIMALS, MONEY_MAX, NEGATIVE, TOO_LARGE, InvalidMoney, parse_money

from .enums import PaymentStatus, PurchaseStatus, ReceptionStatus
from .exceptions import (
    PurchaseCancellationBlocked,
    PurchaseInvalidTransition,
    PurchaseNotEditable,
    PurchaseNotReceivable,
    PurchaseValidationError,
)
from .receipt import Receipt, ReceiptLine

CURRENCY = 'BOB'
REFERENCE_MAX_LENGTH = 100
NOTES_MAX_LENGTH = 2000
REASON_MAX_LENGTH = 500
MAX_ITEMS = 200
QUANTITY_MAX = Decimal('99999999.999')
_QUANTITY_STEP = Decimal('0.001')
_CENTS = Decimal('0.01')
ZERO = Decimal('0.00')
# Solo texto decimal simple: sin exponente, separadores ni dígitos no ASCII (igual que la interfaz).
_PLAIN_DECIMAL = re.compile(r'-?\d+(\.\d+)?', re.ASCII)

# Marca "no enviado" para ediciones parciales (distinta de `None`, que es un valor válido).
UNSET = object()

_MONEY_MESSAGES = {
    NEGATIVE: 'El precio unitario no puede ser negativo.',
    DECIMALS: 'El precio unitario admite como máximo 2 decimales.',
    TOO_LARGE: f'El precio unitario no puede superar {MONEY_MAX}.',
}


def _fail(field_name: str, message: str) -> PurchaseValidationError:
    return PurchaseValidationError({field_name: [message]})


def _text(value: object, field_name: str, label: str, max_length: int) -> str:
    if value is None:
        return ''
    if not isinstance(value, str):
        raise _fail(field_name, f'{label} debe ser texto.')
    value = value.strip()
    if len(value) > max_length:
        raise _fail(field_name, f'{label} no puede superar {max_length} caracteres.')
    return value


def _supplier(value: object) -> UUID:
    if not isinstance(value, UUID):
        raise _fail('supplier_id', 'El proveedor es obligatorio.')
    return value


def _date(value: object) -> date:
    if value is None:
        raise _fail('purchase_date', 'La fecha de compra es obligatoria.')
    if isinstance(value, datetime) or not isinstance(value, date):
        raise _fail('purchase_date', 'La fecha de compra debe ser una fecha válida.')
    return value


def validate_quantity(value: object, allows_fractions: bool = True) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise _fail('quantity', 'La cantidad debe ser un número decimal.')
    if isinstance(value, str) and not _PLAIN_DECIMAL.fullmatch(value.strip()):
        raise _fail('quantity', 'La cantidad debe ser un número decimal.')
    try:
        quantity = Decimal(value.strip() if isinstance(value, str) else value)
    except InvalidOperation:
        raise _fail('quantity', 'La cantidad debe ser un número decimal.') from None
    if not quantity.is_finite():
        raise _fail('quantity', 'La cantidad debe ser un número decimal.')
    if quantity <= 0:
        raise _fail('quantity', 'La cantidad debe ser mayor a cero.')
    if quantity > QUANTITY_MAX:  # antes de `quantize`, que falla con demasiados dígitos
        raise _fail('quantity', f'La cantidad no puede superar {QUANTITY_MAX}.')
    if quantity != quantity.quantize(_QUANTITY_STEP):
        raise _fail('quantity', 'La cantidad admite como máximo 3 decimales.')
    quantity = quantity.quantize(_QUANTITY_STEP)
    if quantity > QUANTITY_MAX:
        raise _fail('quantity', f'La cantidad no puede superar {QUANTITY_MAX}.')
    if not allows_fractions and quantity != quantity.to_integral_value():
        raise _fail('quantity', 'La unidad del producto no admite fracciones: use una cantidad entera.')
    return quantity


def validate_unit_price(value: object) -> Decimal:
    if isinstance(value, str) and not _PLAIN_DECIMAL.fullmatch(value.strip()):
        raise _fail('unit_price', 'El precio unitario debe ser un número decimal.')
    try:
        return parse_money(value)
    except InvalidOperation:  # demasiados dígitos para cuantizar
        raise _fail('unit_price', _MONEY_MESSAGES[TOO_LARGE]) from None
    except InvalidMoney as exc:
        message = _MONEY_MESSAGES.get(exc.code, 'El precio unitario debe ser un número decimal.')
        raise _fail('unit_price', message) from None


def compute_subtotal(quantity: Decimal, unit_price: Decimal) -> Decimal:
    return (quantity * unit_price).quantize(_CENTS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ItemDraft:
    """Línea tal como la pide quien guarda; el snapshot y `allows_fractions` los aporta la capa de aplicación."""

    product_id: UUID
    quantity: object
    unit_price: object
    product_name: str = ''
    unit_abbreviation: str = ''
    allows_fractions: bool = True
    # Problema detectado fuera del dominio (p. ej. producto inexistente o inactivo), asociado a `product_id`.
    product_error: str | None = None


@dataclass
class PurchaseItem:
    """Línea con snapshot del nombre y la unidad del producto; el precio es el acordado con el proveedor."""

    id: UUID
    product_id: UUID
    product_name: str
    unit_abbreviation: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def subtotal(self) -> Decimal:
        return compute_subtotal(self.quantity, self.unit_price)


@dataclass(frozen=True)
class ReceiptLineDraft:
    """Línea de recepción tal como la pide quien registra; `allows_fractions` lo aporta la capa de aplicación."""

    item_id: object
    quantity: object
    allows_fractions: bool = True


def compute_reception_status(items: list[PurchaseItem], received: Mapping[UUID, Decimal]) -> ReceptionStatus:
    """`received` si todas las líneas están completas, `partial` si alguna recibió algo, si no `not_received`."""
    if items and all(received.get(item.id, ZERO) >= item.quantity for item in items):
        return ReceptionStatus.RECEIVED
    if any(received.get(item.id, ZERO) > 0 for item in items):
        return ReceptionStatus.PARTIAL
    return ReceptionStatus.NOT_RECEIVED


def _collect(checks) -> tuple[dict[str, object], dict[str, object]]:
    values: dict[str, object] = {}
    errors: dict[str, object] = {}
    for name, check in checks:
        try:
            values[name] = check()
        except PurchaseValidationError as exc:
            errors.update(exc.errors)
    return values, errors


def _validate_header(supplier_id: object, purchase_date: object, external_reference: object,
                     notes: object) -> tuple[dict[str, object], dict[str, object]]:
    return _collect((
        ('supplier_id', lambda: _supplier(supplier_id)),
        ('purchase_date', lambda: _date(purchase_date)),
        ('external_reference', lambda: _text(external_reference, 'external_reference', 'La referencia externa',
                                             REFERENCE_MAX_LENGTH)),
        ('notes', lambda: _text(notes, 'notes', 'Las notas', NOTES_MAX_LENGTH)),
    ))


def build_items(drafts: list[ItemDraft], existing: list[PurchaseItem] | None = None) -> list[PurchaseItem]:
    """Valida todas las líneas y devuelve los ítems; junta los errores por posición y no deja nada a medias.

    Un producto que ya estaba en la compra conserva su snapshot (nombre y unidad).
    """
    if len(drafts) > MAX_ITEMS:
        raise PurchaseValidationError({'items': [f'Una compra admite como máximo {MAX_ITEMS} líneas.']})
    kept = {item.product_id: item for item in existing or []}
    line_errors: list[dict[str, list[str]]] = []
    items: list[PurchaseItem] = []
    seen: set[UUID] = set()
    total = ZERO
    for draft in drafts:
        values, errors = _collect((
            ('quantity', lambda: validate_quantity(draft.quantity, draft.allows_fractions)),
            ('unit_price', lambda: validate_unit_price(draft.unit_price)),
        ))
        if draft.product_error:
            errors['product_id'] = [draft.product_error]
        elif draft.product_id in seen:
            errors['product_id'] = ['El producto ya está en la compra; modifique su cantidad.']
        seen.add(draft.product_id)
        if not errors:
            subtotal = compute_subtotal(values['quantity'], values['unit_price'])
            total += subtotal
            if subtotal > MONEY_MAX or total > MONEY_MAX:
                errors['quantity'] = ['El importe de la compra supera el máximo permitido.']
        line_errors.append(errors)
        if not errors:
            previous = kept.get(draft.product_id)
            items.append(PurchaseItem(
                id=uuid4(), product_id=draft.product_id,
                product_name=previous.product_name if previous else draft.product_name,
                unit_abbreviation=previous.unit_abbreviation if previous else draft.unit_abbreviation,
                quantity=values['quantity'], unit_price=values['unit_price']))
    if any(line_errors):
        raise PurchaseValidationError({'items': line_errors})
    return items


@dataclass
class Purchase:
    """Agregado raíz de las compras. Cabecera e ítems solo cambian por sus métodos; los importes se derivan."""

    id: UUID
    supplier_id: UUID
    purchase_date: date
    external_reference: str = ''
    notes: str = ''
    status: PurchaseStatus = PurchaseStatus.DRAFT
    items: list[PurchaseItem] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str = ''
    # Los mueven las tasks de recepción y pago; hoy nada los cambia (ADR confirmar-cancelar-compras).
    reception_status: ReceptionStatus = ReceptionStatus.NOT_RECEIVED
    payment_status: PaymentStatus = PaymentStatus.UNPAID

    @classmethod
    def create(cls, supplier_id: object, purchase_date: object, external_reference: object = '',
               notes: object = '', items: list[ItemDraft] | None = None) -> 'Purchase':
        values, errors = _validate_header(supplier_id, purchase_date, external_reference, notes)
        built: list[PurchaseItem] = []
        try:
            built = build_items(items or [])
        except PurchaseValidationError as exc:
            errors.update(exc.errors)
        if errors:
            raise PurchaseValidationError(errors)
        return cls(id=uuid4(), supplier_id=values['supplier_id'], purchase_date=values['purchase_date'],
                   external_reference=values['external_reference'], notes=values['notes'], items=built)

    # --- derivados y estado -----------------------------------------------------------------------------------

    @property
    def total(self) -> Decimal:
        return sum((item.subtotal for item in self.items), ZERO)

    @property
    def editable(self) -> bool:
        return self.status is PurchaseStatus.DRAFT

    def ensure_editable(self) -> None:
        if not self.editable:
            raise PurchaseNotEditable()

    @property
    def reference(self) -> str:
        """Referencia interna provisional derivada del id (la numeración correlativa es otra task)."""
        return f'COM-{self.id.hex[:8].upper()}'

    @property
    def has_activity(self) -> bool:
        return (self.reception_status is not ReceptionStatus.NOT_RECEIVED
                or self.payment_status is not PaymentStatus.UNPAID)

    @property
    def can_cancel(self) -> bool:
        if self.status is PurchaseStatus.DRAFT:
            return True
        return self.status is PurchaseStatus.CONFIRMED and not self.has_activity

    @property
    def can_receive(self) -> bool:
        return self.status is PurchaseStatus.CONFIRMED and self.reception_status is not ReceptionStatus.RECEIVED

    @property
    def allowed_actions(self) -> list[str]:
        if self.status is PurchaseStatus.DRAFT:
            return ['edit', 'confirm', 'cancel']
        actions = ['receive'] if self.can_receive else []
        return actions + ['cancel'] if self.can_cancel else actions

    # --- ciclo de vida ----------------------------------------------------------------------------------------

    def confirm(self, now: datetime, supplier_active: bool = True) -> None:
        """`draft -> confirmed`. El proveedor activo lo informa quien lo conoce (capa de aplicación)."""
        if self.status is not PurchaseStatus.DRAFT:
            raise PurchaseInvalidTransition('Solo un borrador puede confirmarse.')
        errors: dict[str, object] = {}
        if not supplier_active:
            errors['supplier_id'] = ['Selecciona un proveedor activo.']
        if not self.items:
            errors['items'] = ['La compra necesita al menos un producto.']
        if errors:
            raise PurchaseValidationError(errors)
        self.status = PurchaseStatus.CONFIRMED
        self.confirmed_at = now

    def cancel(self, reason: object, now: datetime) -> None:
        """`draft|confirmed -> cancelled`, con motivo y sin recepciones ni pagos."""
        if self.status is PurchaseStatus.CANCELLED:
            raise PurchaseInvalidTransition('La compra ya está cancelada.')
        text = _text(reason, 'reason', 'El motivo de cancelación', REASON_MAX_LENGTH)
        if not text:
            raise _fail('reason', 'El motivo de cancelación es obligatorio.')
        if self.has_activity:
            raise PurchaseCancellationBlocked()
        self.status = PurchaseStatus.CANCELLED
        self.cancelled_at = now
        self.cancellation_reason = text

    def receive(self, receipt_id: UUID, receipt_date: object, today: date, received_before: Mapping[UUID, Decimal],
                drafts: list[ReceiptLineDraft], user_id: UUID | None, user_name: str) -> Receipt:
        """Registra una recepción parcial o completa y recalcula `reception_status`.

        `received_before` es el acumulado confirmado por línea, leído por quien llama bajo el bloqueo de la compra.
        Valida todo junto; si algo falla no cambia nada.
        """
        if self.status is not PurchaseStatus.CONFIRMED:
            raise PurchaseNotReceivable()
        errors: dict[str, object] = {}
        when = None
        if receipt_date is None:
            errors['receipt_date'] = ['La fecha de recepción es obligatoria.']
        elif isinstance(receipt_date, datetime) or not isinstance(receipt_date, date):
            errors['receipt_date'] = ['La fecha de recepción debe ser una fecha válida.']
        elif receipt_date > today:
            errors['receipt_date'] = ['La fecha de recepción no puede ser futura.']
        else:
            when = receipt_date
        lines: list[ReceiptLine] = []
        if not drafts:
            errors['lines'] = ['Indica al menos un producto recibido.']
        else:
            by_id = {item.id: item for item in self.items}
            seen: set[UUID] = set()
            line_errors: list[dict[str, list[str]]] = []
            for draft in drafts:
                item = by_id.get(draft.item_id) if isinstance(draft.item_id, UUID) else None
                problems: dict[str, list[str]] = {}
                if item is None:
                    problems['item_id'] = ['La línea no pertenece a la compra.']
                elif item.id in seen:
                    problems['item_id'] = ['El producto ya está en la recepción.']
                else:
                    seen.add(item.id)
                    try:
                        quantity = validate_quantity(draft.quantity, draft.allows_fractions)
                    except PurchaseValidationError as exc:
                        problems.update(exc.errors)
                    else:
                        pending = item.quantity - received_before.get(item.id, ZERO)
                        if quantity > pending:
                            problems['quantity'] = [f'No puede superar el pendiente ({max(pending, ZERO):f}).']
                        else:
                            lines.append(ReceiptLine(item.id, item.product_id, item.product_name,
                                                     item.unit_abbreviation, quantity))
                line_errors.append(problems)
            if any(line_errors):
                errors['lines'] = line_errors
        if errors:
            raise PurchaseValidationError(errors)
        received = dict(received_before)
        for line in lines:
            received[line.purchase_item_id] = received.get(line.purchase_item_id, ZERO) + line.quantity
        self.reception_status = compute_reception_status(self.items, received)
        return Receipt(id=receipt_id, purchase_id=self.id, receipt_date=when, user_id=user_id, user_name=user_name,
                       lines=lines)

    # --- edición ----------------------------------------------------------------------------------------------

    def update(self, supplier_id: object = UNSET, purchase_date: object = UNSET, external_reference: object = UNSET,
               notes: object = UNSET, items: object = UNSET) -> None:
        """Cambia solo lo enviado; valida todo junto y no modifica nada si algo falla."""
        self.ensure_editable()
        values, errors = _validate_header(
            self.supplier_id if supplier_id is UNSET else supplier_id,
            self.purchase_date if purchase_date is UNSET else purchase_date,
            self.external_reference if external_reference is UNSET else external_reference,
            self.notes if notes is UNSET else notes)
        built = None
        if items is not UNSET:
            try:
                built = build_items(items, self.items)
            except PurchaseValidationError as exc:
                errors.update(exc.errors)
        if errors:
            raise PurchaseValidationError(errors)
        self.supplier_id = values['supplier_id']
        self.purchase_date = values['purchase_date']
        self.external_reference = values['external_reference']
        self.notes = values['notes']
        if built is not None:
            self.items = built
