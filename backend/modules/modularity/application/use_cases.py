from dataclasses import dataclass

from modules.modularity.application.settings_use_cases import MODULES_SCOPE, Actor
from modules.modularity.domain import modules as domain


@dataclass(frozen=True)
class ModuleView:
    definition: domain.ModuleDefinition
    enabled: bool
    requires: list[tuple[domain.ModuleDefinition, bool]]
    optional: list[tuple[domain.ModuleDefinition, bool]]
    missing_requires: list[str]


def _views(enabled: set[str]) -> list[ModuleView]:
    return [
        ModuleView(
            definition=m,
            enabled=m.key in enabled,
            requires=[(domain.BY_KEY[k], k in enabled) for k in m.requires],
            optional=[(domain.BY_KEY[k], k in enabled) for k in m.optional],
            missing_requires=domain.missing_requires(m, enabled),
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
    def __init__(self, repository):
        self.repository = repository

    def execute(self) -> list[ModuleView]:
        return _views(domain.effective_enabled(self.repository.enabled_keys()))


class EnableModule:
    def __init__(self, repository, changes=None):
        self.repository = repository
        self.changes = changes

    def execute(self, key: str, actor: Actor | None = None) -> list[ModuleView]:
        enabled = domain.effective_enabled(self.repository.enabled_keys())
        domain.definition(key)
        if key not in enabled:
            domain.check_can_enable(key, enabled)
            self.repository.enable(key)
            _record(self.changes, actor, key, True)
            enabled.add(key)
        return _views(enabled)


class DisableModule:
    def __init__(self, repository, changes=None):
        self.repository = repository
        self.changes = changes

    def execute(self, key: str, actor: Actor | None = None) -> list[ModuleView]:
        enabled = domain.effective_enabled(self.repository.enabled_keys())
        domain.definition(key)
        if key in enabled:
            domain.check_can_disable(key, enabled)
            self.repository.disable(key)
            _record(self.changes, actor, key, False)
            enabled.discard(key)
        return _views(enabled)
