from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from .enums import InventoryMode, ReceiptStatus
from .exceptions import PurchaseValidationError, ReceiptAlreadyReverted, ReceiptInventoryModeAlreadySet


REVERT_REASON_MAX_LENGTH = 200


@dataclass
class ReceiptLine:
    """Cantidad recibida de una línea de la compra, con snapshot del producto."""

    purchase_item_id: UUID
    product_id: UUID
    product_name: str
    unit_abbreviation: str
    quantity: Decimal


@dataclass
class Receipt:
    """Recepción de mercadería de una compra. Inmutable tras crearse; nace de `Purchase.receive`."""

    id: UUID
    purchase_id: UUID
    receipt_date: date
    user_id: UUID | None
    user_name: str
    lines: list[ReceiptLine] = field(default_factory=list)
    status: ReceiptStatus = ReceiptStatus.CONFIRMED
    warehouse_id: UUID | None = None
    created_at: datetime | None = None
    # Se fija al confirmar y no cambia; None solo en recepciones anteriores sin almacén (modo desconocido).
    inventory_mode: InventoryMode | None = None
    # Datos de la reversión; solo se fijan en `revert`.
    reverted_at: datetime | None = None
    reverted_by_user_id: UUID | None = None
    reverted_by_name: str = ''
    revert_reason: str = ''

    @property
    def reference(self) -> str:
        """Referencia interna provisional derivada del id (la numeración correlativa es otra task)."""
        return f'REC-{self.id.hex[:8].upper()}'

    def set_inventory_mode(self, mode: InventoryMode) -> None:
        """Fija el modo con que se confirmó la recepción; no se puede cambiar después."""
        if self.inventory_mode is not None:
            raise ReceiptInventoryModeAlreadySet()
        self.inventory_mode = mode

    def assign_warehouse(self, warehouse_id: UUID | None) -> None:
        self.warehouse_id = warehouse_id

    @property
    def moved_stock(self) -> bool:
        """¿Generó entradas en el libro de Inventario? Sin modo guardado, solo si tiene almacén."""
        if self.inventory_mode is None:
            return self.warehouse_id is not None
        return self.inventory_mode is InventoryMode.INVENTORY

    def revert(self, reason: object, user_id: UUID | None, user_name: str, now: datetime) -> None:
        """`confirmed → reverted`, con motivo obligatorio (hasta 200 caracteres)."""
        if self.status is ReceiptStatus.REVERTED:
            raise ReceiptAlreadyReverted()
        text = reason.strip() if isinstance(reason, str) else ''
        if not text:
            raise PurchaseValidationError({'reason': ['El motivo es obligatorio.']})
        if len(text) > REVERT_REASON_MAX_LENGTH:
            raise PurchaseValidationError({'reason': [f'El motivo no puede superar {REVERT_REASON_MAX_LENGTH} caracteres.']})
        self.status = ReceiptStatus.REVERTED
        self.reverted_at = now
        self.reverted_by_user_id = user_id
        self.reverted_by_name = user_name
        self.revert_reason = text
