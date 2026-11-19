from django.apps import AppConfig


class ExpensesConfig(AppConfig):
    name = 'modules.expenses'
    label = 'expenses'

    def ready(self):
        from .infrastructure import defaults

        defaults.register()
