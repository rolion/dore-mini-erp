from dataclasses import dataclass
from datetime import date

from modules.modularity.domain import modules as module_domain
from modules.modularity.domain import settings as domain

HISTORY_PAGE_SIZE = 20
MODULES_SCOPE = 'modules'


@dataclass(frozen=True)
class Actor:
    id: int | None
    name: str


@dataclass(frozen=True)
class SettingValue:
    definition: domain.SettingDefinition
    value: str


def _settings_module(key: str) -> module_domain.ModuleDefinition:
    """Módulo con pantalla de configuración: del catálogo y no base (si no, `UnknownModule`)."""
    module = module_domain.definition(key)
    if module.is_base:
        raise module_domain.UnknownModule(key)
    return module


def _values(definitions: list[domain.SettingDefinition], stored: dict[str, str]) -> list[SettingValue]:
    return [SettingValue(d, stored.get(d.key, d.default)) for d in definitions]


class GetModuleSettings:
    def __init__(self, settings):
        self.settings = settings

    def execute(self, module_key: str) -> list[SettingValue]:
        _settings_module(module_key)
        return _values(domain.settings_for(module_key), self.settings.values())


class UpdateModuleSettings:
    """Guarda en bloque (todo o nada) los ajustes de un módulo y registra cada cambio real en el historial."""

    def __init__(self, settings, changes, modules):
        self.settings = settings
        self.changes = changes
        self.modules = modules

    def execute(self, module_key: str, raw: dict[str, object], actor: Actor) -> list[SettingValue]:
        module = _settings_module(module_key)
        enabled = module_domain.effective_enabled(self.modules.enabled_keys())
        if module.key not in enabled:
            raise domain.ModuleDisabled(module.key)
        definitions = domain.settings_for(module_key)
        new_values = domain.validate_all(definitions, raw)
        stored = self.settings.lock_values()
        for definition in definitions:
            if definition.key not in new_values:
                continue
            old = stored.get(definition.key, definition.default)
            new = new_values[definition.key]
            if old == new:
                continue
            self.settings.save(definition.key, new)
            self.changes.add(
                scope=module_key, setting_key=definition.key, setting_label=definition.label,
                old_value=domain.display(definition, old), new_value=domain.display(definition, new),
                actor_id=actor.id, actor_name=actor.name)
            stored[definition.key] = new
        return _values(definitions, stored)


@dataclass(frozen=True)
class HistoryPage:
    count: int
    rows: list
    settings: list[tuple[str, str]]


class ListSettingChanges:
    def __init__(self, changes):
        self.changes = changes

    def execute(self, scope: str, *, date_from: date | None, date_to: date | None, setting_key: str | None,
                page: int) -> HistoryPage:
        if scope == MODULES_SCOPE:
            options = [(f'module.{m.key}', m.name) for m in module_domain.MODULE_CATALOG if not m.is_base]
        else:
            _settings_module(scope)
            options = [(s.key, s.label) for s in domain.settings_for(scope)]
        count, rows = self.changes.list(
            scope, date_from=date_from, date_to=date_to, setting_key=setting_key,
            offset=(page - 1) * HISTORY_PAGE_SIZE, limit=HISTORY_PAGE_SIZE)
        return HistoryPage(count, rows, options)
