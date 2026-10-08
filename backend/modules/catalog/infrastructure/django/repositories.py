from uuid import UUID

from django.db.models import QuerySet

from modules.catalog.domain.product import Product

from .mappers import to_entity, to_model_values
from .models import ProductModel


class ProductList:
    """Vista perezosa de entidades sobre un queryset: permite paginar sin cargar todos los productos."""

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


class DjangoProductRepository:
    def get(self, product_id: UUID) -> Product | None:
        model = ProductModel.objects.filter(pk=product_id).first()
        return to_entity(model) if model else None

    def save(self, product: Product) -> Product:
        model, _ = ProductModel.objects.update_or_create(id=product.id, defaults=to_model_values(product))
        return to_entity(model)

    def list(self, search: str | None = None, active: bool | None = None) -> ProductList:
        queryset = ProductModel.objects.order_by('name', 'id')
        if search:
            queryset = queryset.filter(name__icontains=search)
        if active is not None:
            queryset = queryset.filter(active=active)
        return ProductList(queryset)
