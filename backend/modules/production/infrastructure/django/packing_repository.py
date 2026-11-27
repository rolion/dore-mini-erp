from uuid import UUID

from modules.production.domain.packing import Packing

from .models import PackingModel


def to_entity(model: PackingModel) -> Packing:
    return Packing(
        id=model.id, order_id=model.order_id, request_id=model.request_id, packs=model.packs,
        pack_product_id=model.pack_product_id, pack_product_name=model.pack_product_name,
        bag_product_id=model.bag_product_id, bag_product_name=model.bag_product_name,
        bulk_quantity=model.bulk_quantity, bags_quantity=model.bags_quantity, lot_id=model.lot_id,
        lot_code=model.lot_code, label_product_id=model.label_product_id,
        label_product_name=model.label_product_name, labels_quantity=model.labels_quantity, number=model.number,
        cost_total=model.cost_total, unit_cost=model.unit_cost, created_at=model.created_at,
        created_by_id=model.created_by_id, created_by_name=model.created_by_name)


class DjangoPackingRepository:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _packings(self):
        return PackingModel.objects.filter(company_id=self.company_id)

    def find(self, order_id: UUID, request_id: UUID) -> Packing | None:
        model = self._packings().filter(order_id=order_id, request_id=request_id).first()
        return to_entity(model) if model else None

    def list(self, order_id: UUID) -> list[Packing]:
        return [to_entity(model) for model in self._packings().filter(order_id=order_id).order_by('number')]

    def add(self, packing: Packing) -> Packing:
        """Alta con el siguiente número de la orden; el llamador tiene la orden bloqueada (sin carrera)."""
        last = self._packings().filter(order_id=packing.order_id).order_by('-number').values_list(
            'number', flat=True).first() or 0
        model = PackingModel.objects.create(
            id=packing.id, company_id=self.company_id, order_id=packing.order_id, number=last + 1,
            request_id=packing.request_id, packs=packing.packs, pack_product_id=packing.pack_product_id,
            pack_product_name=packing.pack_product_name, bag_product_id=packing.bag_product_id,
            bag_product_name=packing.bag_product_name, bulk_quantity=packing.bulk_quantity,
            bags_quantity=packing.bags_quantity, lot_id=packing.lot_id, lot_code=packing.lot_code,
            label_product_id=packing.label_product_id, label_product_name=packing.label_product_name,
            labels_quantity=packing.labels_quantity, cost_total=packing.cost_total,
            unit_cost=packing.unit_cost, created_by_id=packing.created_by_id,
            created_by_name=packing.created_by_name)
        return to_entity(model)
