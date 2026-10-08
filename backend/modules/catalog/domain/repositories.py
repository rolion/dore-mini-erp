from typing import Protocol, Sequence
from uuid import UUID

from .product import Product


class ProductRepository(Protocol):
    def get(self, product_id: UUID) -> Product | None: ...

    def save(self, product: Product) -> Product:
        """Persiste el producto y lo devuelve con los datos que asigna la persistencia (timestamps)."""
        ...

    def list(self, search: str | None = None, active: bool | None = None) -> Sequence[Product]:
        """Productos ordenados por nombre e id; `search` es coincidencia parcial sin distinguir mayúsculas."""
        ...
