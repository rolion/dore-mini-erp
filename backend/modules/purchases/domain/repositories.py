from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence
from uuid import UUID

from .enums import PaymentStatus, PurchaseStatus, ReceptionStatus
from .payment import Payment
from .purchase import Purchase
from .receipt import Receipt
from .supplier import Supplier


@dataclass(frozen=True)
class PurchaseSummary:
    """Fila de la lista de compras: datos de cabecera, total y número de líneas."""

    id: UUID
    purchase_date: date
    supplier_id: UUID
    supplier_name: str
    external_reference: str
    total: Decimal
    status: PurchaseStatus
    items_count: int
    reference: str = ''
    # Seguimiento: solo para compras confirmadas; en borrador o cancelada son `None`.
    reception_status: ReceptionStatus | None = None
    payment_status: PaymentStatus | None = None
    paid_total: Decimal | None = None
    balance: Decimal | None = None


@dataclass(frozen=True)
class PurchaseFilters:
    """Filtros combinables (AND) de la lista de compras.

    Recepción y pago solo existen en compras confirmadas: filtrar por ellos excluye borradores y canceladas.
    `pending_payment` es «pago pendiente»: `unpaid` o `partial`.
    """

    supplier_id: UUID | None = None
    date_from: date | None = None
    date_to: date | None = None
    status: PurchaseStatus | None = None
    reception_status: ReceptionStatus | None = None
    payment_status: PaymentStatus | None = None
    pending_payment: bool = False
    search: str = ''


class PurchaseRepository(Protocol):
    def get(self, purchase_id: UUID, for_update: bool = False) -> Purchase | None: ...

    def save(self, purchase: Purchase) -> Purchase:
        """Persiste la compra con sus líneas (las reemplaza) y la devuelve con los datos que asigna la persistencia."""
        ...

    def list(self, supplier_id: UUID | None = None,
             filters: PurchaseFilters | None = None) -> Sequence[PurchaseSummary]:
        """Compras de la empresa: fecha desc, creación desc, id; opcionalmente de un proveedor y con filtros."""
        ...


class ReceiptRepository(Protocol):
    def get(self, receipt_id: UUID) -> Receipt | None:
        """Recepción de la empresa por id (de cualquier compra)."""
        ...

    def save(self, receipt: Receipt) -> Receipt: ...

    def list_for_purchase(self, purchase_id: UUID) -> Sequence[Receipt]:
        """Recepciones de la compra: fecha desc, creación desc, id."""
        ...

    def received_totals(self, purchase_id: UUID) -> dict[UUID, Decimal]:
        """Acumulado de recepciones confirmadas por línea de la compra."""
        ...


class PaymentRepository(Protocol):
    def get(self, payment_id: UUID) -> Payment | None:
        """Pago de la empresa por id (de cualquier compra)."""
        ...

    def save(self, payment: Payment) -> Payment: ...

    def list_for_purchase(self, purchase_id: UUID) -> Sequence[Payment]:
        """Pagos de la compra: fecha desc, creación desc, id."""
        ...

    def paid_total(self, purchase_id: UUID) -> Decimal:
        """Suma de los pagos confirmados de la compra."""
        ...


class SupplierRepository(Protocol):
    def get(self, supplier_id: UUID) -> Supplier | None: ...

    def save(self, supplier: Supplier) -> Supplier:
        """Persiste el proveedor y lo devuelve con los datos que asigna la persistencia (timestamps)."""
        ...

    def list(self, search: str | None = None, active: bool | None = None) -> Sequence[Supplier]:
        """Proveedores ordenados por nombre e id; `search` es coincidencia parcial por nombre o identificación."""
        ...
