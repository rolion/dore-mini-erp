# Django descubre los modelos del app desde este módulo; la definición vive en infraestructura.
from modules.inventory.infrastructure.django.models import (  # noqa: F401
    StockAdjustmentModel,
    StockMovementModel,
    WarehouseModel,
)
