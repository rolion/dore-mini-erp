from django.apps import AppConfig


class CostingConfig(AppConfig):
    name = 'modules.costing'
    label = 'costing'

    def ready(self) -> None:
        from shared import stock_valuation

        from .infrastructure.provider import CostingValuationProvider

        stock_valuation.register(CostingValuationProvider())
