"""Fachada pública del módulo Purchases para otros módulos (p. ej. las compras).

Es la única vía de entrada entre módulos: devuelve DTO inmutables, nunca entidades ni modelos.
"""
from dataclasses import dataclass
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
