from django.apps import AppConfig


class DentistryConfig(AppConfig):
    name = 'modules.dentistry'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from modules.agenda.services import register_guard
        from .infrastructure.agenda_guard import appointment_guard
        register_guard(appointment_guard)
