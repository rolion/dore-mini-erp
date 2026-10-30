from collections.abc import Iterable

from modules.purchases.domain.enums import PaymentStatus, PurchaseStatus, ReceptionStatus
from modules.purchases.domain.purchase import Purchase, PurchaseItem
from modules.purchases.domain.supplier import Supplier

from .models import PurchaseItemModel, PurchaseModel, SupplierModel


def to_entity(model: SupplierModel) -> Supplier:
    return Supplier(
        id=model.id,
        name=model.name,
        tax_id=model.tax_id,
        phone=model.phone,
        email=model.email,
        notes=model.notes,
        active=model.active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def to_model_values(supplier: Supplier) -> dict[str, object]:
    return {
        'name': supplier.name,
        'tax_id': supplier.tax_id,
        'phone': supplier.phone,
        'email': supplier.email,
        'notes': supplier.notes,
        'active': supplier.active,
    }


def purchase_to_entity(model: PurchaseModel, items: Iterable[PurchaseItemModel]) -> Purchase:
    return Purchase(
        id=model.id,
        supplier_id=model.supplier_id,
        purchase_date=model.purchase_date,
        external_reference=model.external_reference,
        notes=model.notes,
        status=PurchaseStatus(model.status),
        items=[PurchaseItem(id=i.id, product_id=i.product_id, product_name=i.product_name,
                            unit_abbreviation=i.unit_abbreviation, quantity=i.quantity, unit_price=i.unit_price)
               for i in items],
        created_at=model.created_at,
        updated_at=model.updated_at,
        confirmed_at=model.confirmed_at,
        cancelled_at=model.cancelled_at,
        cancellation_reason=model.cancellation_reason,
        reception_status=ReceptionStatus(model.reception_status),
        payment_status=PaymentStatus(model.payment_status),
    )


def purchase_to_model_values(purchase: Purchase) -> dict[str, object]:
    return {
        'supplier_id': purchase.supplier_id,
        'purchase_date': purchase.purchase_date,
        'external_reference': purchase.external_reference,
        'notes': purchase.notes,
        'status': purchase.status.value,
        'total': purchase.total,
        'confirmed_at': purchase.confirmed_at,
        'cancelled_at': purchase.cancelled_at,
        'cancellation_reason': purchase.cancellation_reason,
        'reception_status': purchase.reception_status.value,
        'payment_status': purchase.payment_status.value,
    }
