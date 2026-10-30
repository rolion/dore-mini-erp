from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from .enums import InventoryMode, ReceiptStatus
from .exceptions import ReceiptInventoryModeAlreadySet


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
