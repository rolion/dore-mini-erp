from dataclasses import dataclass

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


class ListModules:
    def __init__(self, repository):
        self.repository = repository

    def execute(self) -> list[ModuleView]:
        return _views(domain.effective_enabled(self.repository.enabled_keys()))


class EnableModule:
    def __init__(self, repository):
        self.repository = repository

    def execute(self, key: str) -> list[ModuleView]:
        enabled = domain.effective_enabled(self.repository.enabled_keys())
        domain.definition(key)
        if key not in enabled:
            domain.check_can_enable(key, enabled)
            self.repository.enable(key)
            enabled.add(key)
        return _views(enabled)


class DisableModule:
    def __init__(self, repository):
        self.repository = repository

    def execute(self, key: str) -> list[ModuleView]:
        enabled = domain.effective_enabled(self.repository.enabled_keys())
        domain.definition(key)
        if key in enabled:
            domain.check_can_disable(key, enabled)
            self.repository.disable(key)
            enabled.discard(key)
        return _views(enabled)
