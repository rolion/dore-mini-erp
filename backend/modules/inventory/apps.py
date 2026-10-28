from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = 'modules.inventory'
    label = 'inventory'

    def ready(self) -> None:
        from shared import stock_history

        from .infrastructure.django.stock_repository import has_movements

        # Catálogo consulta este puerto para bloquear cambios de unidad/control de stock con historial.
        stock_history.register(has_movements)
