from uuid import UUID

from django.db import transaction
from django.db.models import Count, QuerySet

from modules.purchases.domain.enums import PurchaseStatus
from modules.purchases.domain.purchase import Purchase
from modules.purchases.domain.repositories import PurchaseSummary

from .mappers import purchase_to_entity, purchase_to_model_values
from .models import PurchaseItemModel, PurchaseModel, SupplierModel


class PurchaseList:
    """Vista perezosa de resúmenes sobre un queryset: permite paginar sin cargar todas las compras."""

    def __init__(self, company_id: UUID, queryset: QuerySet):
        self._company_id = company_id
        self._queryset = queryset

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def _summaries(self, models) -> list[PurchaseSummary]:
        models = list(models)
        names = dict(SupplierModel.objects.filter(
            company_id=self._company_id, pk__in={m.supplier_id for m in models}).values_list('id', 'name'))
        return [PurchaseSummary(
            id=m.id, purchase_date=m.purchase_date, supplier_id=m.supplier_id,
            supplier_name=names.get(m.supplier_id, ''), external_reference=m.external_reference, total=m.total,
            status=PurchaseStatus(m.status), items_count=m.items_count) for m in models]

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self._summaries(self._queryset[index])
        return self._summaries([self._queryset[index]])[0]

    def __iter__(self):
        return iter(self._summaries(self._queryset))


class DjangoPurchaseRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id` y `save` lo establece al crear."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _purchases(self) -> QuerySet:
        return PurchaseModel.objects.filter(company_id=self.company_id)

    def get(self, purchase_id: UUID, for_update: bool = False) -> Purchase | None:
        queryset = self._purchases()
        if for_update:
            queryset = queryset.select_for_update()
        model = queryset.filter(pk=purchase_id).first()
        if model is None:
            return None
        return purchase_to_entity(model, model.items.all())

    @transaction.atomic
    def save(self, purchase: Purchase) -> Purchase:
        model, _ = PurchaseModel.objects.update_or_create(
            id=purchase.id, company_id=self.company_id, defaults=purchase_to_model_values(purchase))
        model.items.all().delete()
        PurchaseItemModel.objects.bulk_create([
            PurchaseItemModel(
                id=item.id, purchase=model, position=position, product_id=item.product_id,
                product_name=item.product_name, unit_abbreviation=item.unit_abbreviation,
                quantity=item.quantity, unit_price=item.unit_price, subtotal=item.subtotal)
            for position, item in enumerate(purchase.items)])
        return purchase_to_entity(model, model.items.all())

    def list(self, supplier_id: UUID | None = None) -> PurchaseList:
        queryset = self._purchases().annotate(items_count=Count('items')).order_by(
            '-purchase_date', '-created_at', 'id')
        if supplier_id is not None:
            queryset = queryset.filter(supplier_id=supplier_id)
        return PurchaseList(self.company_id, queryset)
