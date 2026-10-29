from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from modules.purchases.domain.exceptions import PurchaseNotFound, PurchaseValidationError
from modules.purchases.domain.purchase import UNSET, ItemDraft, Purchase
from modules.purchases.domain.repositories import PurchaseRepository, SupplierRepository

from .ports import ProductCatalog

PRODUCT_MISSING = 'El producto no existe.'
PRODUCT_INACTIVE = 'El producto está inactivo.'
SUPPLIER_NOT_ACTIVE = 'Selecciona un proveedor activo.'


@dataclass(frozen=True)
class ItemInput:
    product_id: UUID
    quantity: object
    unit_price: object


def _supplier_errors(suppliers: SupplierRepository, supplier_id: object) -> dict[str, list[str]]:
    """Regla entre agregados: el proveedor debe existir en la empresa y estar activo."""
    if not isinstance(supplier_id, UUID):
        return {}  # lo informa el dominio (obligatorio)
    supplier = suppliers.get(supplier_id)
    if supplier is None or not supplier.active:
        return {'supplier_id': [SUPPLIER_NOT_ACTIVE]}
    return {}


def _drafts(products: ProductCatalog, items: Sequence[ItemInput], kept_product_ids: set[UUID]) -> list[ItemDraft]:
    """Líneas con los datos del catálogo: un producto nuevo debe estar activo; uno que ya estaba en el borrador, no."""
    info = products.get_products([item.product_id for item in items])
    drafts = []
    for item in items:
        product = info.get(item.product_id)
        error = None
        if product is None:
            error = PRODUCT_MISSING
        elif not product.active and item.product_id not in kept_product_ids:
            error = PRODUCT_INACTIVE
        drafts.append(ItemDraft(
            product_id=item.product_id, quantity=item.quantity, unit_price=item.unit_price,
            product_name=product.name if product else '',
            unit_abbreviation=(product.unit_abbreviation or '') if product else '',
            allows_fractions=True if product is None or product.unit_abbreviation is None
            else product.allows_fractions,
            product_error=error))
    return drafts


def _merge(errors: dict[str, object], extra: dict[str, list[str]]) -> dict[str, object]:
    return {**extra, **errors}


class CreatePurchase:
    def __init__(self, purchases: PurchaseRepository, suppliers: SupplierRepository, products: ProductCatalog):
        self.purchases = purchases
        self.suppliers = suppliers
        self.products = products

    def execute(self, supplier_id: object = None, purchase_date: object = None, external_reference: object = '',
                notes: object = '', items: Sequence[ItemInput] = ()) -> Purchase:
        extra = _supplier_errors(self.suppliers, supplier_id)
        drafts = _drafts(self.products, items, set())
        try:
            purchase = Purchase.create(supplier_id=supplier_id, purchase_date=purchase_date,
                                       external_reference=external_reference, notes=notes, items=drafts)
        except PurchaseValidationError as exc:
            raise PurchaseValidationError(_merge(exc.errors, extra)) from exc
        if extra:
            raise PurchaseValidationError(extra)
        return self.purchases.save(purchase)


class UpdatePurchase:
    """Edición parcial del borrador; `items`, si se envía, reemplaza todas las líneas."""

    def __init__(self, purchases: PurchaseRepository, suppliers: SupplierRepository, products: ProductCatalog):
        self.purchases = purchases
        self.suppliers = suppliers
        self.products = products

    def execute(self, purchase_id: UUID, supplier_id: object = UNSET, purchase_date: object = UNSET,
                external_reference: object = UNSET, notes: object = UNSET,
                items: Sequence[ItemInput] | object = UNSET) -> Purchase:
        purchase = self.purchases.get(purchase_id, for_update=True)
        if purchase is None:
            raise PurchaseNotFound(purchase_id)
        purchase.ensure_editable()
        extra = _supplier_errors(self.suppliers, purchase.supplier_id if supplier_id is UNSET else supplier_id)
        drafts = UNSET
        if items is not UNSET:
            drafts = _drafts(self.products, items, {item.product_id for item in purchase.items})
        try:
            purchase.update(supplier_id=supplier_id, purchase_date=purchase_date,
                            external_reference=external_reference, notes=notes, items=drafts)
        except PurchaseValidationError as exc:
            raise PurchaseValidationError(_merge(exc.errors, extra)) from exc
        if extra:
            raise PurchaseValidationError(extra)
        return self.purchases.save(purchase)
