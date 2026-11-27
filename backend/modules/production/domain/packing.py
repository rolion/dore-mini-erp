"""Empaque de cuñapés a granel en packs de 6 (sin Django): registro inmutable de una tanda."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from .production_order import OrderValidationError, ProductionOrder

UNITS_PER_PACK = 6
BAGS_PER_PACK = 1
LABELS_PER_PACK = 1
PACKS_MAX = 99999
PACKS_ERROR = 'La cantidad de packs debe ser un entero positivo.'


def parse_packs(raw: object) -> int:
    """Entero positivo hasta `PACKS_MAX`; rechaza `bool`, decimales y texto no numérico."""
    if isinstance(raw, bool):
        raise ValueError(PACKS_ERROR)
    if isinstance(raw, str):
        text = raw.strip()
        if not (text.isascii() and text.isdigit()) or len(text) > 9:
            raise ValueError(PACKS_ERROR)
        value = int(text)
    elif isinstance(raw, int):
        value = raw
    else:
        raise ValueError(PACKS_ERROR)
    if value < 1:
        raise ValueError(PACKS_ERROR)
    if value > PACKS_MAX:
        raise ValueError(f'La cantidad de packs no puede superar {PACKS_MAX}.')
    return value


@dataclass(frozen=True)
class ProductRef:
    id: UUID
    name: str


@dataclass
class Packing:
    id: UUID
    order_id: UUID
    request_id: UUID
    packs: int
    pack_product_id: UUID
    pack_product_name: str
    bag_product_id: UUID
    bag_product_name: str
    bulk_quantity: Decimal
    bags_quantity: Decimal
    lot_id: UUID
    lot_code: str
    label_product_id: UUID | None = None
    label_product_name: str = ''
    labels_quantity: Decimal = Decimal('0')
    number: int | None = None
    cost_total: Decimal | None = None
    unit_cost: Decimal | None = None
    created_at: datetime | None = None
    created_by_id: UUID | None = None
    created_by_name: str = ''

    @classmethod
    def create(cls, order: ProductionOrder, *, request_id: UUID, packs: object, pack: ProductRef | None,
               bag: ProductRef | None, user_id: UUID | None, user_name: str, label: ProductRef | None = None,
               label_requested: bool = False) -> 'Packing':
        """Valida la tanda (INV-02, INV-03) y calcula las cantidades; `pack`/`bag`/`label` son `None` si no
        existen. La etiqueta es opcional: `label_requested` indica que se eligió una (INV-08)."""
        errors: dict = {}
        count = 0
        try:
            count = parse_packs(packs)
        except ValueError as exc:
            errors['packs'] = [str(exc)]
        if pack is None:
            errors['pack_product_id'] = ['El producto pack no existe, está inactivo o no controla stock.']
        if bag is None:
            errors['bag_product_id'] = ['El producto bolsa no existe, está inactivo o no controla stock.']
        if pack is not None and pack.id == order.result_product_id:
            errors['pack_product_id'] = ['El pack no puede ser el producto a granel de la orden.']
        if bag is not None and bag.id == order.result_product_id:
            errors['bag_product_id'] = ['La bolsa no puede ser el producto a granel de la orden.']
        if pack is not None and bag is not None and pack.id == bag.id:
            errors['bag_product_id'] = ['La bolsa y el pack deben ser productos distintos.']
        if label_requested and label is None:
            errors['label_product_id'] = ['El producto etiqueta no existe, está inactivo o no controla stock.']
        if label is not None:
            if label.id == order.result_product_id:
                errors['label_product_id'] = ['La etiqueta no puede ser el producto a granel de la orden.']
            elif pack is not None and label.id == pack.id or bag is not None and label.id == bag.id:
                errors['label_product_id'] = ['La etiqueta debe ser un producto distinto del pack y de la bolsa.']
        if errors:
            raise OrderValidationError(errors)
        return cls(
            id=uuid4(), order_id=order.id, request_id=request_id, packs=count, pack_product_id=pack.id,
            pack_product_name=pack.name, bag_product_id=bag.id, bag_product_name=bag.name,
            bulk_quantity=Decimal(count * UNITS_PER_PACK), bags_quantity=Decimal(count * BAGS_PER_PACK),
            lot_id=order.lot_id, lot_code=order.lot_code, created_by_id=user_id, created_by_name=user_name,
            label_product_id=label.id if label else None, label_product_name=label.name if label else '',
            labels_quantity=Decimal(count * LABELS_PER_PACK) if label else Decimal('0'))

    def record_cost(self, total: Decimal | None, unit_cost: Decimal | None) -> None:
        self.cost_total = total
        self.unit_cost = unit_cost
