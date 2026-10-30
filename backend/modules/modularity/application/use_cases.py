from dataclasses import dataclass, field
from datetime import datetime

from modules.modularity.application.settings_use_cases import MODULES_SCOPE, Actor
from modules.modularity.domain import modules as domain


class NoExtensions:
    """Sin extensiones: ninguna capacidad disponible, sin bloqueos ni ganchos (fail-closed)."""

    def available_capabilities(self, keys) -> set[str]:
        return set()

    def disable_blockers(self, module_key: str) -> list:
        return []

    def on_enabled(self, module_key: str, adopted_at) -> None:
        return None


@dataclass(frozen=True)
class ModuleView:
    definition: domain.ModuleDefinition
    enabled: bool
    requires: list[tuple[domain.ModuleDefinition, bool]]
    optional: list[tuple[domain.ModuleDefinition, bool]]
    missing_requires: list[str]
    capabilities: list[tuple[str, str, bool]] = field(default_factory=list)  # (clave, etiqueta, disponible)
    missing_capabilities: list[str] = field(default_factory=list)
    adopted_at: datetime | None = None
    blockers: list = field(default_factory=list)


def _views(enabled: set[str], extensions, adopted: dict | None = None) -> list[ModuleView]:
    needed = {c for m in domain.MODULE_CATALOG for c in m.requires_capabilities}
    available = extensions.available_capabilities(needed) if needed else set()
    adopted = adopted or {}
    return [
        ModuleView(
            definition=m,
            enabled=m.key in enabled,
            requires=[(domain.BY_KEY[k], k in enabled) for k in m.requires],
            optional=[(domain.BY_KEY[k], k in enabled) for k in m.optional],
            missing_requires=domain.missing_requires(m, enabled),
            capabilities=[(c, domain.CAPABILITIES[c], c in available) for c in m.requires_capabilities],
            missing_capabilities=domain.missing_capabilities(m, available),
            adopted_at=adopted.get(m.key) if m.records_adoption and m.key in enabled else None,
            blockers=extensions.disable_blockers(m.key) if m.key in enabled and not m.is_base else [],
        )
        for m in domain.MODULE_CATALOG
    ]


def _record(changes, actor: Actor | None, key: str, enabled: bool) -> None:
    """Deja en el historial el cambio de estado de un módulo (solo si hay actor e historial)."""
    if changes is None or actor is None:
        return
    states = {True: 'Habilitado', False: 'Deshabilitado'}
    changes.add(scope=MODULES_SCOPE, setting_key=f'module.{key}', setting_label=domain.BY_KEY[key].name,
                old_value=states[not enabled], new_value=states[enabled], actor_id=actor.id, actor_name=actor.name)


class ListModules:
    def __init__(self, repository, extensions=None):
        self.repository = repository
        self.extensions = extensions or NoExtensions()

    def execute(self) -> list[ModuleView]:
        enabled = domain.effective_enabled(self.repository.enabled_keys())
        return _views(enabled, self.extensions, self.repository.enabled_at())


class EnableModule:
    def __init__(self, repository, changes=None, extensions=None):
        self.repository = repository
        self.changes = changes
        self.extensions = extensions or NoExtensions()

    def execute(self, key: str, actor: Actor | None = None) -> list[ModuleView]:
        enabled = domain.effective_enabled(self.repository.enabled_keys())
        module = domain.definition(key)
        if key not in enabled:
            available = self.extensions.available_capabilities(module.requires_capabilities)
            domain.check_can_enable(key, enabled, available)
            self.repository.enable(key)
            if module.records_adoption:
                # La fecha de adopción rige desde aquí: el gancho valora las existencias actuales, sin recalcular lo anterior.
                self.extensions.on_enabled(key, self.repository.enabled_at()[key])
            _record(self.changes, actor, key, True)
            enabled.add(key)
        return _views(enabled, self.extensions, self.repository.enabled_at())


class DisableModule:
    def __init__(self, repository, changes=None, extensions=None):
        self.repository = repository
        self.changes = changes
        self.extensions = extensions or NoExtensions()

    def execute(self, key: str, actor: Actor | None = None) -> list[ModuleView]:
        enabled = domain.effective_enabled(self.repository.enabled_keys())
        domain.definition(key)
        if key in enabled:
            domain.check_can_disable(key, enabled, self.extensions.disable_blockers(key))
            self.repository.disable(key)
            _record(self.changes, actor, key, False)
            enabled.discard(key)
        return _views(enabled, self.extensions, self.repository.enabled_at())
