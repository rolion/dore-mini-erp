from decimal import Decimal
from uuid import UUID

from rest_framework import status
from rest_framework.exceptions import APIException

from modules.inventory.domain.exceptions import InsufficientStock
from modules.inventory.infrastructure.adapters import CatalogProductDirectory
from modules.inventory.infrastructure.django.repositories import DjangoWarehouseRepository

QUANTITY_PLACES = Decimal('0.001')


def _quantity(value: Decimal) -> str:
    return format(value.quantize(QUANTITY_PLACES), 'f')


class InsufficientStockConflict(APIException):
    """409 `insufficient_stock` con producto, almacén, cantidad solicitada y existencia actual."""

    status_code = status.HTTP_409_CONFLICT

    def __init__(self, exc: InsufficientStock, company_id: UUID):
        product = CatalogProductDirectory(company_id).get_products([exc.product_id]).get(exc.product_id)
        warehouse = DjangoWarehouseRepository(company_id).get(exc.warehouse_id)
        super().__init__({
            'detail': str(exc), 'code': exc.code,
            'product': {'id': str(exc.product_id), 'name': product.name if product else ''},
            'warehouse': {'id': str(exc.warehouse_id), 'name': warehouse.name if warehouse else ''},
            'unit': {'abbreviation': product.unit_abbreviation if product else None},
            'requested': _quantity(exc.requested),
            'available': _quantity(exc.available),
        })
