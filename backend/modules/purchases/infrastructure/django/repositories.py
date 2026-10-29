from uuid import UUID

from django.db.models import Q, QuerySet

from modules.purchases.domain.supplier import Supplier

from .mappers import to_entity, to_model_values
from .models import SupplierModel


class SupplierList:
    """Vista perezosa de entidades sobre un queryset: permite paginar sin cargar todos los proveedores."""

    def __init__(self, queryset: QuerySet):
        self._queryset = queryset

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [to_entity(model) for model in self._queryset[index]]
        return to_entity(self._queryset[index])

    def __iter__(self):
        return (to_entity(model) for model in self._queryset)


class DjangoSupplierRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id` y `save` lo establece al crear."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _suppliers(self) -> QuerySet:
        return SupplierModel.objects.filter(company_id=self.company_id)

    def get(self, supplier_id: UUID) -> Supplier | None:
        model = self._suppliers().filter(pk=supplier_id).first()
        return to_entity(model) if model else None

    def save(self, supplier: Supplier) -> Supplier:
        model, _ = SupplierModel.objects.update_or_create(
            id=supplier.id, company_id=self.company_id, defaults=to_model_values(supplier))
        return to_entity(model)

    def list(self, search: str | None = None, active: bool | None = None) -> SupplierList:
        queryset = self._suppliers().order_by('name', 'id')
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(tax_id__icontains=search))
        if active is not None:
            queryset = queryset.filter(active=active)
        return SupplierList(queryset)
