from django.apps import AppConfig


class ModularityConfig(AppConfig):
    name = 'modules.modularity'
    label = 'modularity'

    def ready(self):
        from shared import module_gate

        from .infrastructure import defaults
        from .infrastructure.django.gate import enabled_keys

        module_gate.register(enabled_keys)
        defaults.register()
