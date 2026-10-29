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
    """409 `insufficient_stock` con producto, almacén, cantidad solicitada y existencia actual.

    Los campos de primer nivel describen la primera línea faltante (contrato de ajustes y apertura); `lines`
    lista todas las líneas sin saldo.
    """

    status_code = status.HTTP_409_CONFLICT

    def __init__(self, exc: InsufficientStock, company_id: UUID):
        products = CatalogProductDirectory(company_id).get_products([s.product_id for s in exc.shortages])
        warehouse = DjangoWarehouseRepository(company_id).get(exc.warehouse_id)

        def line(shortage) -> dict:
            product = products.get(shortage.product_id)
            return {
                'product': {'id': str(shortage.product_id), 'name': product.name if product else ''},
                'unit': {'abbreviation': product.unit_abbreviation if product else None},
                'requested': _quantity(shortage.requested),
                'available': _quantity(shortage.available),
            }

        lines = [line(s) for s in exc.shortages]
        super().__init__({
            'detail': str(exc), 'code': exc.code,
            'product': lines[0]['product'],
            'warehouse': {'id': str(exc.warehouse_id), 'name': warehouse.name if warehouse else ''},
            'unit': lines[0]['unit'],
            'requested': lines[0]['requested'],
            'available': lines[0]['available'],
            'lines': lines,
        })
