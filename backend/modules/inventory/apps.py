from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = 'modules.inventory'
    label = 'inventory'

    def ready(self):
        from shared import stock_history

        from .services import has_history

        # Con movimientos registrados, Catálogo deja de permitir cambiar el control de stock o la unidad base.
        stock_history.register(has_history)
