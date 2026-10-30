from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, QuerySet

from modules.catalog.domain.exceptions import UnitValidationError
from modules.catalog.domain.product import Product
from modules.catalog.domain.unit import UnitOfMeasure

from .mappers import to_entity, to_model_values, unit_to_entity, unit_to_model_values
from .models import ProductModel, UnitModel


UNCLASSIFIED = 'unclassified'


class ProductList:
    """Vista perezosa de entidades sobre un queryset: permite paginar sin cargar todos los productos."""

    def __init__(self, queryset: QuerySet, convert=to_entity):
        self._queryset = queryset
        self._convert = convert

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self._convert(model) for model in self._queryset[index]]
        return self._convert(self._queryset[index])

    def __iter__(self):
        return (self._convert(model) for model in self._queryset)


class DjangoProductRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id` y `save` lo establece al crear."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _products(self) -> QuerySet:
        return ProductModel.objects.filter(company_id=self.company_id).select_related('base_unit')

    def get(self, product_id: UUID) -> Product | None:
        model = self._products().filter(pk=product_id).first()
        return to_entity(model) if model else None

    def save(self, product: Product) -> Product:
        ProductModel.objects.update_or_create(
            id=product.id, company_id=self.company_id, defaults=to_model_values(product))
        return to_entity(self._products().get(pk=product.id))

    def list(self, search: str | None = None, active: bool | None = None, tracks_stock: bool | None = None,
             can_buy: bool | None = None, can_sell: bool | None = None,
             category: str | None = None) -> ProductList:
        queryset = self._products().order_by('name', 'id')
        if search:
            queryset = queryset.filter(name__icontains=search)
        if active is not None:
            queryset = queryset.filter(active=active)
        if tracks_stock is not None:
            queryset = queryset.filter(tracks_stock=tracks_stock)
        if can_buy is not None:
            queryset = queryset.filter(can_buy=can_buy)
        if can_sell is not None:
            queryset = queryset.filter(can_sell=can_sell)
        if category == UNCLASSIFIED:
            queryset = queryset.filter(category__isnull=True)
        elif category:
            queryset = queryset.filter(category=category)
        return ProductList(queryset)


class DjangoUnitRepository:
    """Repositorio de unidades de medida acotado a una empresa."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _units(self) -> QuerySet:
        in_use = Exists(ProductModel.objects.filter(base_unit_id=OuterRef('pk')))
        return UnitModel.objects.filter(company_id=self.company_id).annotate(in_use=in_use)

    def get(self, unit_id: UUID) -> UnitOfMeasure | None:
        model = self._units().filter(pk=unit_id).first()
        return unit_to_entity(model) if model else None

    def save(self, unit: UnitOfMeasure) -> UnitOfMeasure:
        duplicates = self._units().exclude(pk=unit.id)
        errors: dict[str, list[str]] = {}
        if duplicates.filter(name__iexact=unit.name).exists():
            errors['name'] = ['Ya existe una unidad con ese nombre.']
        if duplicates.filter(abbreviation__iexact=unit.abbreviation).exists():
            errors['abbreviation'] = ['Ya existe una unidad con esa abreviatura.']
        if errors:
            raise UnitValidationError(errors)
        try:
            with transaction.atomic():
                UnitModel.objects.update_or_create(
                    id=unit.id, company_id=self.company_id, defaults=unit_to_model_values(unit))
        except IntegrityError:  # carrera con otra petición: la restricción única manda
            raise UnitValidationError({'name': ['Ya existe una unidad con ese nombre o abreviatura.']}) from None
        return unit_to_entity(self._units().get(pk=unit.id))

    def list(self, search: str | None = None, active: bool | None = None) -> ProductList:
        queryset = self._units().order_by('name', 'id')
        if search:
            queryset = queryset.filter(name__icontains=search)
        if active is not None:
            queryset = queryset.filter(active=active)
        return ProductList(queryset, convert=unit_to_entity)
