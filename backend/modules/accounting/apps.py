from django.apps import AppConfig


class AccountingConfig(AppConfig):
    name = 'modules.accounting'
    label = 'accounting'

    def ready(self):
        from shared import enable_preconditions

        from .services import missing_method_labels

        # Habilitar Contabilidad exige el mapeo método → cuenta completo (PB-ACC-001).
        enable_preconditions.register('accounting', missing_method_labels)
