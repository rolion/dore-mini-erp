"""Puertos que Purchases necesita de otros módulos. Su implementación vive en `infrastructure/adapters.py`."""
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ProductInfo:
    id: UUID
    name: str
    active: bool
    can_buy: bool
    unit_abbreviation: str | None
    allows_fractions: bool


class ProductCatalog(Protocol):
    def get_products(self, product_ids: Iterable[UUID]) -> dict[UUID, ProductInfo]: ...


@dataclass(frozen=True)
class Actor:
    user_id: UUID | None
    user_name: str


@dataclass(frozen=True)
class StockProductInfo:
    id: UUID
    name: str
    unit_abbreviation: str | None


@dataclass(frozen=True)
class StockWarehouse:
    id: UUID
    name: str
    is_default: bool


@dataclass(frozen=True)
class StockEntryMovement:
    id: UUID
    product_id: UUID
    product_name: str
    unit_abbreviation: str | None
    warehouse_id: UUID
    warehouse_name: str
    quantity: Decimal
    reference: str = ''
    status: str = 'confirmed'
    reversed_by_id: UUID | None = None
    reversed_by_reference: str = ''


class StockEntry(Protocol):
    """Entradas de inventario al recibir; integración opcional (solo con el módulo Inventario habilitado)."""

    def is_available(self) -> bool: ...

    def controlled_products(self, product_ids: Iterable[UUID]) -> dict[UUID, StockProductInfo]: ...

    def active_warehouses(self) -> list[StockWarehouse]: ...

    def register_entries(self, warehouse_id: UUID, lines: list[tuple[UUID, Decimal]], receipt_id: UUID,
                         reference: str, actor: Actor) -> None:
        """Una entrada por línea; lanza `PurchaseValidationError` con `warehouse_id` si el almacén no sirve."""
        ...

    def movements_for(self, receipt_id: UUID) -> list[StockEntryMovement]: ...

    def reverse_entries(self, receipt_id: UUID, reason: str, actor: Actor) -> None:
        """Revierte todas las entradas de la recepción, todas o ninguna; lanza `StockShortage` si falta saldo."""
        ...


@dataclass(frozen=True)
class ClassificationInfo:
    id: UUID
    name: str
    direction: str
    active: bool


class ClassificationGateway(Protocol):
    """Clasificaciones de egreso de Contabilidad (integración por su fachada, en `infrastructure/adapters.py`)."""

    def validate_expense_classification(self, classification_id: UUID) -> ClassificationInfo:
        """Lanza `PurchaseValidationError` (`classification_id`) si no es de la empresa, está inactiva o no egreso."""
        ...

    def describe(self, classification_ids: Iterable[UUID]) -> dict[UUID, ClassificationInfo]: ...

    def is_covered(self, on: date) -> bool:
        """¿Contabilidad debe crear movimiento para una operación con esa fecha efectiva?"""
        ...


@dataclass(frozen=True)
class PostedEntry:
    """El asiento contable de una recepción (DTO de lectura)."""
    id: UUID
    accounting_date: date
    total: Decimal


class PurchasePosting(Protocol):
    """Contabilización de la recepción de mercadería (COM-02); integración opcional con Contabilidad."""

    def is_available(self) -> bool:
        """¿Está habilitada Contabilidad? (solo para decidir si se muestra el asiento)."""
        ...

    def covers(self, on: date) -> bool:
        """¿Contabilidad está habilitada y una operación con esa fecha debe crear asiento?"""
        ...

    def recognize_receipt(self, purchase, receipt, amount: Decimal, actor: Actor,
                          advance_applied: Decimal = Decimal('0')) -> None:
        """Debe Inventario / Haber Cuentas por pagar por `amount` (y Haber Anticipos por `advance_applied`).

        Dentro de la transacción del llamador. Sin cobertura no hace nada; lanza `PostingRejected` si Contabilidad
        lo rechaza (configuración, período).
        """
        ...

    def record_payment(self, purchase, payment, debt: Decimal, advance: Decimal, actor: Actor) -> None:
        """Asientos del pago: `PURCHASE_PAYMENT` por `debt` y `PURCHASE_ADVANCE` por `advance` (los de importe 0 no)."""
        ...

    def preview_payment(self, purchase, amount: Decimal, method: str, on: date, debt: Decimal,
                        advance: Decimal) -> 'PaymentPreview':
        """Asiento previsto del pago sin escribir nada."""
        ...

    def payment_entries(self, payment_ids: Iterable[UUID]) -> dict[UUID, list['PostedPaymentEntry']]:
        """Asientos de cada pago (0-2); los pagos sin asiento no aparecen."""
        ...

    def reverse_receipt(self, purchase, receipt, reason: str, actor: Actor) -> None:
        """Revierte el asiento de la recepción con sus cuentas originales; sin asiento no hace nada."""
        ...

    def recognized_totals(self, receipt_ids: Iterable[UUID]) -> dict[UUID, Decimal]:
        """Total del asiento de reconocimiento de cada recepción que lo tiene (las demás no aparecen)."""
        ...

    def entry_for(self, receipt_id: UUID) -> PostedEntry | None: ...


@dataclass(frozen=True)
class PostedPaymentEntry:
    id: UUID
    kind: str  # 'debt' | 'advance'
    accounting_date: date
    total: Decimal


@dataclass(frozen=True)
class PaymentPreviewLine:
    side: str  # DEBIT | CREDIT
    role: str
    account_name: str
    amount: Decimal


@dataclass(frozen=True)
class PaymentPreview:
    """Vista previa del asiento de un pago: reparto, líneas y faltantes (cada uno con `code`, `role`, `message`)."""
    covered: bool
    debt_amount: Decimal
    advance_amount: Decimal
    lines: tuple[PaymentPreviewLine, ...] = ()
    issues: tuple[dict, ...] = ()
