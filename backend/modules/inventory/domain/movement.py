from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from uuid import UUID, uuid4

from .exceptions import MovementConflict, MovementValidationError

QUANTITY_DECIMALS = Decimal('0.0001')
MAX_TEXT_LENGTH = 200


class MovementKind(str, Enum):
    IN = 'in'
    OUT = 'out'

    @property
    def opposite(self) -> 'MovementKind':
        return MovementKind.OUT if self is MovementKind.IN else MovementKind.IN


class MovementStatus(str, Enum):
    CONFIRMED = 'confirmed'
    REVERSED = 'reversed'


@dataclass(frozen=True)
class SourceTypeDefinition:
    key: str
    label: str
    module: str  # módulo de negocio propietario del documento de origen


SOURCE_TYPES: dict[str, SourceTypeDefinition] = {
    d.key: d for d in (
        SourceTypeDefinition('sales_order', 'Pedido de venta', 'sales'),
        SourceTypeDefinition('purchase_receipt', 'Recepción de compra', 'purchases'),
        SourceTypeDefinition('inventory_adjustment', 'Ajuste de inventario', 'inventory'),
        SourceTypeDefinition('inventory_opening', 'Apertura de existencias', 'inventory'),
    )
}


@dataclass(frozen=True)
class MovementSource:
    """Operación de origen que causó el movimiento: clase de documento, su id y (opcional) la línea."""

    type: str
    id: str
    line: str = ''

    def __post_init__(self):
        if self.type not in SOURCE_TYPES:
            raise MovementValidationError({'source': ['Clase de origen desconocida.']})
        if not str(self.id).strip():
            raise MovementValidationError({'source': ['El documento de origen es obligatorio.']})


def parse_quantity(value: object) -> Decimal:
    if isinstance(value, float):
        raise MovementValidationError({'quantity': ['La cantidad debe enviarse como Decimal, no como float.']})
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise MovementValidationError({'quantity': ['La cantidad no es un número válido.']}) from None
    if not quantity.is_finite() or quantity <= 0:
        raise MovementValidationError({'quantity': ['La cantidad debe ser mayor que cero.']})
    if quantity != quantity.quantize(QUANTITY_DECIMALS):
        raise MovementValidationError({'quantity': ['La cantidad admite hasta 4 decimales.']})
    return quantity.quantize(QUANTITY_DECIMALS)


def _text(value: str | None, field_name: str) -> str:
    text = (value or '').strip()
    if len(text) > MAX_TEXT_LENGTH:
        raise MovementValidationError({field_name: [f'No puede superar {MAX_TEXT_LENGTH} caracteres.']})
    return text


def _reversal_reason(value: str | None) -> str:
    """El motivo de una reversión es obligatorio (no vacío tras recortar, hasta 200 caracteres)."""
    reason = _text(value, 'reason')
    if not reason:
        raise MovementValidationError({'reason': ['El motivo es obligatorio.']})
    return reason


@dataclass
class StockMovement:
    """Registro inmutable de una entrada o salida. Lo único que cambia tras crearlo es `confirmed → reversed`."""

    id: UUID
    product_id: UUID
    warehouse_id: UUID
    kind: MovementKind
    quantity: Decimal
    occurred_at: datetime
    user_id: UUID | None
    user_name: str
    reference: str = ''
    reason: str = ''
    source: MovementSource | None = None
    status: MovementStatus = MovementStatus.CONFIRMED
    reverses_id: UUID | None = None
    created_at: datetime | None = None
    reversed_by_id: UUID | None = field(default=None, compare=False)

    @classmethod
    def record(cls, *, product_id: UUID, warehouse_id: UUID, kind: MovementKind, quantity: object,
               occurred_at: datetime, user_id: UUID | None, user_name: str, reference: str = '',
               reason: str = '', source: MovementSource | None = None) -> 'StockMovement':
        return cls(
            id=uuid4(), product_id=product_id, warehouse_id=warehouse_id, kind=MovementKind(kind),
            quantity=parse_quantity(quantity), occurred_at=occurred_at, user_id=user_id,
            user_name=_text(user_name, 'user_name'), reference=_text(reference, 'reference'),
            reason=_text(reason, 'reason'), source=source)

    @property
    def signed_quantity(self) -> Decimal:
        return self.quantity if self.kind is MovementKind.IN else -self.quantity

    def reverse(self, *, occurred_at: datetime, user_id: UUID | None, user_name: str,
                reason: str) -> 'StockMovement':
        """Marca este movimiento como revertido y devuelve el contramovimiento (opuesto, vinculado).

        El contramovimiento no repite el origen: se vincula por `reverses_id` y no choca con la idempotencia.
        """
        if self.status is MovementStatus.REVERSED:
            raise MovementConflict('already_reversed', 'El movimiento ya fue revertido.')
        if self.reverses_id is not None:
            raise MovementConflict('cannot_reverse_reversal', 'Un contramovimiento no se puede revertir.')
        reason = _reversal_reason(reason)
        self.status = MovementStatus.REVERSED
        return StockMovement(
            id=uuid4(), product_id=self.product_id, warehouse_id=self.warehouse_id, kind=self.kind.opposite,
            quantity=self.quantity, occurred_at=occurred_at, user_id=user_id, user_name=_text(user_name, 'user_name'),
            reference=self.reference, reason=reason,
            source=None, reverses_id=self.id)


_BLOCKED_SOURCES = {
    'sales_order': ('requires_return',
                    'Las salidas por venta requieren una devolución, que aún no está disponible.'),
    'purchase_receipt': ('reverse_from_origin',
                         'Este movimiento proviene de una recepción: corrígelo desde la recepción en Compras.'),
}


def reversal_block(movement: StockMovement) -> tuple[str, str] | None:
    """`(código, mensaje)` si el movimiento no se puede revertir desde Inventario; `None` si se puede."""
    if movement.status is MovementStatus.REVERSED:
        return 'already_reversed', 'El movimiento ya fue revertido.'
    if movement.reverses_id is not None:
        return 'cannot_reverse_reversal', 'Un contramovimiento no se puede revertir.'
    if movement.source is not None and movement.source.type in _BLOCKED_SOURCES:
        return _BLOCKED_SOURCES[movement.source.type]
    return None
