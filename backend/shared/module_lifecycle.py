"""Puerto neutro del ciclo de vida de un módulo en una empresa.

Quien dueñe un módulo (p. ej. Contabilidad) registra al arrancar sus ganchos; `modularity` solo los consulta, de modo
que no importa módulos de negocio. Sin ganchos registrados no ocurre nada (comportamiento previo).
"""
from collections.abc import Callable
from uuid import UUID

Hook = Callable[[UUID], None]
Blockers = Callable[[UUID], list[str]]

_on_enabled: dict[str, Hook] = {}
_on_disabled: dict[str, Hook] = {}
_blockers: dict[str, Blockers] = {}


def register(module_key: str, *, on_enabled: Hook | None = None, on_disabled: Hook | None = None,
             disable_blockers: Blockers | None = None) -> None:
    if on_enabled:
        _on_enabled[module_key] = on_enabled
    if on_disabled:
        _on_disabled[module_key] = on_disabled
    if disable_blockers:
        _blockers[module_key] = disable_blockers


def enabled(company_id: UUID, module_key: str) -> None:
    hook = _on_enabled.get(module_key)
    if hook:
        hook(company_id)


def disabled(company_id: UUID, module_key: str) -> None:
    hook = _on_disabled.get(module_key)
    if hook:
        hook(company_id)


def disable_blockers(company_id: UUID, module_key: str) -> list[str]:
    """Motivos que impiden deshabilitar el módulo en la empresa; vacío si se puede."""
    checker = _blockers.get(module_key)
    return list(checker(company_id)) if checker else []
