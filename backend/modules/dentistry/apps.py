from django.apps import AppConfig


class DentistryConfig(AppConfig):
    name = 'modules.dentistry'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from .infrastructure.adapters import register_agenda_guard
        register_agenda_guard()
