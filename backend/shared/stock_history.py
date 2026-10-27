"""Puerto neutro para saber si un producto tiene historial de movimientos de inventario.

Quien guarde los movimientos (Inventario, cuando existan) registra el proveedor al arrancar; Catálogo solo consulta
este puerto, de modo que ningún módulo de negocio importa al otro. Sin proveedor no hay historial: hoy no existen
movimientos, por lo que no se bloquea nada (a diferencia de `module_gate`, esto no es un permiso).
"""
from collections.abc import Callable
from uuid import UUID

Provider = Callable[[UUID, UUID], bool]

_provider: Provider | None = None


def register(provider: Provider | None) -> None:
    global _provider
    _provider = provider


def has_history(company_id: UUID, product_id: UUID) -> bool:
    """Verdadero si el producto de la empresa tiene movimientos previos."""
    if _provider is None:
        return False
    return bool(_provider(company_id, product_id))
