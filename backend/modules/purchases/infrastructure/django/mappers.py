from modules.purchases.domain.supplier import Supplier

from .models import SupplierModel


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
