from typing import Sequence
from uuid import UUID

from modules.inventory.domain.exceptions import WarehouseConflict, WarehouseNotFound, WarehouseValidationError
from modules.inventory.domain.repositories import WarehouseRepository
from modules.inventory.domain.warehouse import Warehouse

from .ports import WarehouseActivity

UNSET = object()


def _get(repository: WarehouseRepository, warehouse_id: UUID) -> Warehouse:
    warehouse = repository.get(warehouse_id)
    if warehouse is None:
        raise WarehouseNotFound(warehouse_id)
    return warehouse


class ListWarehouses:
    def __init__(self, repository: WarehouseRepository):
        self.repository = repository

    def execute(self, search: str | None = None, active: bool | None = None) -> Sequence[Warehouse]:
        self.repository.ensure_default()
        return self.repository.list(search=search, active=active)


class GetWarehouse:
    def __init__(self, repository: WarehouseRepository):
        self.repository = repository

    def execute(self, warehouse_id: UUID) -> Warehouse:
        self.repository.ensure_default()
        return _get(self.repository, warehouse_id)


class CreateWarehouse:
    def __init__(self, repository: WarehouseRepository):
        self.repository = repository

    def execute(self, name: object, description: str = '', is_default: bool = False) -> Warehouse:
        self.repository.ensure_default()
        warehouse = Warehouse.create(name=name, description=description)
        if is_default:
            warehouse.make_default()
        return self.repository.save(warehouse)


class UpdateWarehouse:
    def __init__(self, repository: WarehouseRepository):
        self.repository = repository

    def execute(self, warehouse_id: UUID, name: object = UNSET, description: object = UNSET,
                is_default: object = UNSET) -> Warehouse:
        warehouse = _get(self.repository, warehouse_id)
        if is_default is False and warehouse.is_default:
            raise WarehouseValidationError(
                {'is_default': ['Para cambiar el predeterminado, define otro almacén como predeterminado.']})
        if name is not UNSET:
            warehouse.rename(name)
        if description is not UNSET:
            warehouse.describe(description)
        if is_default is True and not warehouse.is_default:
            warehouse.make_default()
        return self.repository.save(warehouse)


class ActivateWarehouse:
    def __init__(self, repository: WarehouseRepository):
        self.repository = repository

    def execute(self, warehouse_id: UUID) -> Warehouse:
        warehouse = _get(self.repository, warehouse_id)
        warehouse.activate()
        return self.repository.save(warehouse)


class DeactivateWarehouse:
    def __init__(self, repository: WarehouseRepository, activity: WarehouseActivity):
        self.repository = repository
        self.activity = activity

    def execute(self, warehouse_id: UUID) -> Warehouse:
        # Bajo el bloqueo del almacén: un movimiento simultáneo no puede dejar saldo en un almacén que se desactiva.
        with self.repository.locked(warehouse_id):
            warehouse = _get(self.repository, warehouse_id)
            if self.activity.has_nonzero_balance(warehouse.id):
                raise WarehouseConflict(
                    'warehouse_has_stock', 'No se puede desactivar: el almacén tiene saldo distinto de cero.')
            if self.activity.has_pending_receipts(warehouse.id):
                raise WarehouseConflict(
                    'warehouse_pending_receipts', 'No se puede desactivar: el almacén tiene recepciones pendientes.')
            warehouse.deactivate()
            return self.repository.save(warehouse)


class MakeDefaultWarehouse:
    def __init__(self, repository: WarehouseRepository):
        self.repository = repository

    def execute(self, warehouse_id: UUID) -> Warehouse:
        warehouse = _get(self.repository, warehouse_id)
        warehouse.make_default()
        return self.repository.save(warehouse)
