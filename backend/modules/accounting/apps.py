from django.apps import AppConfig


class AccountingConfig(AppConfig):
    name = 'modules.accounting'
    label = 'accounting'

    def ready(self):
        from shared import module_lifecycle

        from .infrastructure import defaults, lifecycle

        module_lifecycle.register('accounting', on_enabled=lifecycle.on_enabled, on_disabled=lifecycle.on_disabled,
                                  disable_blockers=lifecycle.disable_blockers)
        defaults.register()
