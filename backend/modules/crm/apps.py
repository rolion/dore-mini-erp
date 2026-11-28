from django.apps import AppConfig


class CrmConfig(AppConfig):
    name = 'modules.crm'
    label = 'crm'

    def ready(self):
        from .infrastructure import defaults

        defaults.register()
        from .infrastructure import inbox_subscriber

        inbox_subscriber.register()
