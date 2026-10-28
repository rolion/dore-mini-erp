from contextlib import contextmanager
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from modules.inventory.domain.exceptions import WarehouseConflict, WarehouseValidationError
from modules.inventory.domain.warehouse import DEFAULT_WAREHOUSE_NAME, Warehouse

from .models import WarehouseModel


def to_entity(model: WarehouseModel) -> Warehouse:
    return Warehouse(
        id=model.id, name=model.name, description=model.description, active=model.active,
        is_default=model.is_default, created_at=model.created_at, updated_at=model.updated_at)


class WarehouseList:
    """Vista perezosa de entidades sobre un queryset (paginable sin cargar todo)."""

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


class DjangoWarehouseRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _warehouses(self) -> QuerySet:
        return WarehouseModel.objects.filter(company_id=self.company_id)

    def get(self, warehouse_id: UUID) -> Warehouse | None:
        model = self._warehouses().filter(pk=warehouse_id).first()
        return to_entity(model) if model else None

    def save(self, warehouse: Warehouse) -> Warehouse:
        if self._warehouses().exclude(pk=warehouse.id).filter(name__iexact=warehouse.name).exists():
            raise WarehouseValidationError({'name': ['Ya existe un almacén con ese nombre.']})
        try:
            with transaction.atomic():
                if warehouse.is_default:
                    self._warehouses().exclude(pk=warehouse.id).filter(is_default=True).update(is_default=False)
                WarehouseModel.objects.update_or_create(
                    id=warehouse.id, company_id=self.company_id,
                    defaults={'name': warehouse.name, 'description': warehouse.description,
                              'active': warehouse.active, 'is_default': warehouse.is_default})
        except IntegrityError:  # carrera con otra petición: la restricción única manda
            if self._warehouses().exclude(pk=warehouse.id).filter(name__iexact=warehouse.name).exists():
                raise WarehouseValidationError({'name': ['Ya existe un almacén con ese nombre.']}) from None
            raise WarehouseConflict(
                'warehouse_default_changed',
                'El almacén predeterminado cambió al mismo tiempo; inténtalo de nuevo.') from None
        return to_entity(self._warehouses().get(pk=warehouse.id))

    def list(self, search: str | None = None, active: bool | None = None) -> WarehouseList:
        queryset = self._warehouses().order_by('name', 'id')
        if search:
            queryset = queryset.filter(name__icontains=search)
        if active is not None:
            queryset = queryset.filter(active=active)
        return WarehouseList(queryset)

    @contextmanager
    def locked(self, warehouse_id: UUID):
        with transaction.atomic():
            list(self._warehouses().select_for_update().filter(pk=warehouse_id))
            yield

    def ensure_default(self) -> None:
        if self._warehouses().exists():
            return
        try:
            with transaction.atomic():
                WarehouseModel.objects.create(
                    company_id=self.company_id, name=DEFAULT_WAREHOUSE_NAME, is_default=True)
        except IntegrityError:  # otra petición la sembró al mismo tiempo
            pass
