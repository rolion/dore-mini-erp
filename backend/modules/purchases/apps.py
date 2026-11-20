from django.apps import AppConfig


class PurchasesConfig(AppConfig):
    name = 'modules.purchases'
    label = 'purchases'

    def ready(self):
        from .infrastructure import defaults

        defaults.register()
