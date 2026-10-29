from typing import Sequence
from uuid import UUID

from modules.purchases.domain.exceptions import SupplierNotFound
from modules.purchases.domain.repositories import SupplierRepository
from modules.purchases.domain.supplier import Supplier


class GetSupplier:
    def __init__(self, repository: SupplierRepository):
        self.repository = repository

    def execute(self, supplier_id: UUID) -> Supplier:
        supplier = self.repository.get(supplier_id)
        if supplier is None:
            raise SupplierNotFound(supplier_id)
        return supplier


class ListSuppliers:
    def __init__(self, repository: SupplierRepository):
        self.repository = repository

    def execute(self, search: str | None = None, active: bool | None = None) -> Sequence[Supplier]:
        return self.repository.list(search=search, active=active)
