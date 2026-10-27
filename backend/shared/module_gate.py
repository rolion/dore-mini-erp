"""Puerto neutro para saber qué módulos tiene habilitados una empresa.

Lo implementa `modularity` (se registra al arrancar) y lo consultan el permiso por módulo y las integraciones
opcionales entre módulos, de modo que ningún módulo de negocio importa a `modularity`.
"""
from collections.abc import Callable, Collection
from uuid import UUID

Provider = Callable[[UUID], Collection[str]]

_provider: Provider | None = None


class GateNotConfigured(Exception):
    """No se registró quién responde por los módulos habilitados: nunca se concede acceso por omisión."""


def register(provider: Provider) -> None:
    global _provider
    _provider = provider


def enabled_keys(company_id: UUID) -> frozenset[str]:
    """Claves de los módulos habilitados de la empresa (incluye los base)."""
    if _provider is None:
        raise GateNotConfigured('No hay un proveedor de módulos habilitados registrado.')
    return frozenset(_provider(company_id))


def is_enabled(company_id: UUID, key: str) -> bool:
    return key in enabled_keys(company_id)
