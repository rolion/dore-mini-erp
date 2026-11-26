from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.inventory.application.lot_use_cases import GetLot, ListLots
from modules.inventory.domain.exceptions import LotNotFound
from modules.inventory.domain.lot import LotPosition, LotStatus
from modules.inventory.domain.repositories import LotFilters
from modules.inventory.infrastructure.adapters import CatalogProductDirectory
from modules.inventory.infrastructure.django.lot_repository import DjangoStockLotRepository
from shared.tenancy import company_id_from

from .lot_serializers import LotSerializer
from .pagination import WarehousePagination
from .stock_views import _unit, _uuid_param

LOT_NOT_FOUND = 'Lote no encontrado.'
STATUS_FILTERS = {status.value: status for status in LotStatus}


def _lot_filters(request) -> LotFilters:
    """Convierte los query params de Lotes en un filtro tipado; lo inválido da 400 por parámetro."""
    params = request.query_params
    errors: dict[str, list[str]] = {}
    status = None
    if params.get('status'):
        status = STATUS_FILTERS.get(params['status'])
        if status is None:
            errors['status'] = ['Valor inválido: use refrigerating o released.']
    with_stock = params.get('with_stock') or 'false'
    if with_stock not in ('true', 'false'):
        errors['with_stock'] = ['Valor inválido: use true o false.']
    ids: dict[str, object] = {}
    for name in ('product_id', 'warehouse_id'):
        try:
            ids[name] = _uuid_param(request, name, required=False)
        except ValidationError as exc:
            errors.update(exc.detail)
    if errors:
        raise ValidationError(errors)
    return LotFilters(search=(params.get('search') or '').strip() or None, product_id=ids['product_id'],
                      warehouse_id=ids['warehouse_id'], status=status, with_stock=with_stock == 'true')


def _rows(company_id, positions: list[LotPosition]) -> list[dict]:
    products = CatalogProductDirectory(company_id).get_products({p.lot.product_id for p in positions})
    rows = []
    for position in positions:
        lot = position.lot
        product = products.get(lot.product_id)
        rows.append({
            'id': lot.id, 'code': lot.code, 'status': lot.status.value, 'lot_date': lot.lot_date,
            'fiscal_period_name': lot.number.period_name, 'product_id': lot.product_id,
            'product_name': product.name if product else '', 'product_active': product.active if product else False,
            'unit': _unit(product), 'warehouse_id': lot.warehouse_id, 'warehouse_name': position.warehouse_name,
            'physical_quantity': position.physical, 'available_quantity': position.available,
            'created_at': lot.created_at, 'released_at': lot.released_at,
            'released_by_name': lot.released_by_name,
        })
    return rows


class LotListView(APIView):
    """Lotes con su saldo físico y su disponible para empaque (solo lectura)."""

    required_modules = ('inventory',)

    def get(self, request):
        filters = _lot_filters(request)
        company_id = company_id_from(request)
        lots = ListLots(DjangoStockLotRepository(company_id)).execute(filters)
        paginator = WarehousePagination()
        page = paginator.paginate_queryset(lots, request, view=self)
        return paginator.get_paginated_response(LotSerializer(_rows(company_id, page), many=True).data)


class LotDetailView(APIView):
    required_modules = ('inventory',)

    def get(self, request, lot_id):
        company_id = company_id_from(request)
        try:
            position = GetLot(DjangoStockLotRepository(company_id)).execute(lot_id)
        except LotNotFound as exc:
            raise NotFound(LOT_NOT_FOUND) from exc
        return Response(LotSerializer(_rows(company_id, [position])[0]).data)
