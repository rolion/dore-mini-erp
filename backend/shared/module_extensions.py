"""Puerto neutro de extensiones de módulos: capacidades, guardas de desactivación y ganchos de habilitación.

Lo consulta `modularity` y lo registran los módulos que ofrecen una capacidad (p. ej. Inventario: valoración) o que
tienen datos que impiden deshabilitarlos (p. ej. Producción: órdenes abiertas), de modo que nadie importa a nadie.
Sin proveedor registrado la capacidad no está disponible y no hay bloqueos (fail-closed solo en capacidades).
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Blocker:
    code: str
    message: str
    resolution: str


CapabilityProvider = Callable[[UUID], bool]
DisableGuard = Callable[[UUID], list[Blocker]]
EnableHook = Callable[[UUID, datetime], None]

_capabilities: dict[str, CapabilityProvider] = {}
_disable_guards: dict[str, list[DisableGuard]] = {}
_enable_hooks: dict[str, list[EnableHook]] = {}


def register_capability(key: str, provider: CapabilityProvider) -> None:
    _capabilities[key] = provider


def register_disable_guard(module_key: str, guard: DisableGuard) -> None:
    _disable_guards.setdefault(module_key, []).append(guard)


def register_enable_hook(module_key: str, hook: EnableHook) -> None:
    _enable_hooks.setdefault(module_key, []).append(hook)


def capability_available(company_id: UUID, key: str) -> bool:
    provider = _capabilities.get(key)
    return bool(provider and provider(company_id))


def disable_blockers(company_id: UUID, module_key: str) -> list[Blocker]:
    return [b for guard in _disable_guards.get(module_key, []) for b in guard(company_id)]


def run_enable_hooks(company_id: UUID, module_key: str, adopted_at: datetime) -> None:
    for hook in _enable_hooks.get(module_key, []):
        hook(company_id, adopted_at)


def reset() -> None:
    """Solo para pruebas: olvida todos los registros."""
    _capabilities.clear()
    _disable_guards.clear()
    _enable_hooks.clear()
