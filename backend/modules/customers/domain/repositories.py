from typing import Protocol, Sequence
from uuid import UUID

from .customer import Customer


class CustomerRepository(Protocol):
    def get(self, customer_id: UUID) -> Customer | None: ...

    def save(self, customer: Customer) -> Customer:
        """Persiste el cliente y lo devuelve con los datos que asigna la persistencia (timestamps)."""
        ...

    def list(self, search: str | None = None, active: bool | None = None) -> Sequence[Customer]:
        """Clientes ordenados por nombre e id.

        `search` es coincidencia parcial sin distinguir mayúsculas por nombre; si contiene dígitos,
        también por teléfono comparando solo sus dígitos.
        """
        ...

    def find_by_phone(self, phone: str, exclude_id: UUID | None = None, limit: int = 10) -> Sequence[Customer]:
        """Clientes (activos o inactivos) cuyo teléfono almacenado es exactamente `phone`."""
        ...
