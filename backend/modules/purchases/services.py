"""Fachada pública del módulo Purchases para otros módulos (p. ej. las compras).

Es la única vía de entrada entre módulos: devuelve DTO inmutables, nunca entidades ni modelos.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from modules.purchases.infrastructure.django.repositories import DjangoSupplierRepository

DEFAULT_ACTIVE_LIMIT = 50


@dataclass(frozen=True)
class SupplierForPurchase:
    id: UUID
    name: str
    active: bool


def get_supplier_for_purchase(company_id: UUID, supplier_id: UUID) -> SupplierForPurchase | None:
    """El proveedor de la empresa con su estado vigente, o `None` si no existe (o es de otra empresa).

    La regla de "proveedor activo" la aplica quien compra, no la fachada: una compra histórica sigue
    pudiendo mostrar un proveedor desactivado.
    """
    supplier = DjangoSupplierRepository(company_id).get(supplier_id)
    if supplier is None:
        return None
    return SupplierForPurchase(id=supplier.id, name=supplier.name, active=supplier.active)


def list_active_suppliers(company_id: UUID, search: str | None = None,
                          limit: int = DEFAULT_ACTIVE_LIMIT) -> list[SupplierForPurchase]:
    """Proveedores activos de la empresa para el selector de una compra nueva, por nombre."""
    suppliers = DjangoSupplierRepository(company_id).list(search=search or None, active=True)[:limit]
    return [SupplierForPurchase(id=s.id, name=s.name, active=s.active) for s in suppliers]


# --- Escritura para la importación de ventas (TASK-cargar-ventas-desde-archivo) -----------------------------

def list_suppliers_for_import(company_id: UUID) -> list[SupplierForPurchase]:
    """Todos los proveedores de la empresa (activos e inactivos) para casar por nombre; solo lectura."""
    return [SupplierForPurchase(id=s.id, name=s.name, active=s.active)
            for s in DjangoSupplierRepository(company_id).list()]


def create_supplier_for_import(company_id: UUID, name: str) -> SupplierForPurchase:
    """Crea un proveedor solo con nombre, con el caso de uso de Compras."""
    from modules.purchases.application.commands import CreateSupplier

    from modules.purchases.domain.exceptions import SupplierValidationError
    from shared.import_errors import ImportRejected, first_error

    try:
        supplier = CreateSupplier(DjangoSupplierRepository(company_id)).execute(name=name)
    except SupplierValidationError as exc:
        field, message = first_error(exc.errors)
        raise ImportRejected('supplier_rejected', message, field) from exc
    return SupplierForPurchase(id=supplier.id, name=supplier.name, active=supplier.active)


@dataclass(frozen=True)
class ImportedPurchase:
    id: UUID
    total: str


def import_received_purchase(company_id: UUID, *, supplier_id: UUID, purchase_date,
                             lines: list[tuple[UUID, Decimal, Decimal]], warehouse_id: UUID | None,
                             user_id: UUID | None, user_name: str, post_accounting: bool = True,
                             external_reference: str = '') -> ImportedPurchase:
    """Crea, confirma y recibe por completo una compra (entradas de stock con costo y, con cobertura, el asiento de
    reconocimiento Debe Inventario / Haber Cuentas por pagar). **No registra pago**: queda por pagar.

    Cada línea es `(producto, cantidad, costo unitario)`. Corre en la transacción de quien llama. Con
    `post_accounting=False` no genera ningún asiento. Lanza `shared.import_errors.ImportRejected`.
    """
    from django.utils import timezone

    from modules.purchases.application.purchase_commands import ConfirmPurchase, CreatePurchase, ItemInput
    from modules.purchases.application.receipt_commands import ReceiptLineInput, RegisterReception
    from modules.purchases.application.ports import Actor
    from modules.purchases.domain import exceptions as errors
    from modules.purchases.infrastructure.adapters import (
        ProductCatalogAdapter,
        PurchasePostingAdapter,
        StockEntryAdapter,
    )
    from modules.purchases.infrastructure.django.repositories import (
        DjangoPaymentRepository,
        DjangoPurchaseRepository,
        DjangoReceiptRepository,
    )
    from uuid import uuid4

    from shared.import_errors import ImportRejected, first_error

    purchases = DjangoPurchaseRepository(company_id)
    suppliers = DjangoSupplierRepository(company_id)
    receipts = DjangoReceiptRepository(company_id)
    actor = Actor(user_id, user_name)
    try:
        purchase = CreatePurchase(purchases, suppliers, ProductCatalogAdapter(company_id)).execute(
            supplier_id=supplier_id, purchase_date=purchase_date, external_reference=external_reference,
            notes='Compra inferida por importación de ventas',
            items=[ItemInput(product_id, quantity, unit_cost) for product_id, quantity, unit_cost in lines])
        purchase = ConfirmPurchase(purchases, suppliers).execute(purchase.id, timezone.now())
        receipt, _ = RegisterReception(
            purchases, receipts, ProductCatalogAdapter(company_id), StockEntryAdapter(company_id),
            PurchasePostingAdapter(company_id) if post_accounting else None, DjangoPaymentRepository(company_id),
        ).execute(purchase.id, uuid4(), purchase_date,
                  [ReceiptLineInput(item.id, item.quantity) for item in purchase.items],
                  warehouse_id, actor, timezone.localdate())
    except errors.PostingRejected as exc:
        raise ImportRejected(exc.code, str(exc)) from exc
    except errors.PurchaseValidationError as exc:
        field, message = first_error(exc.errors)
        raise ImportRejected('purchase_rejected', message, field) from exc
    except (errors.PurchaseNotReceivable, errors.PurchaseNotEditable, errors.PurchaseInvalidTransition) as exc:
        raise ImportRejected('purchase_rejected', 'No se pudo registrar la compra inferida.') from exc
    return ImportedPurchase(id=purchase.id, total=str(purchase.total))
