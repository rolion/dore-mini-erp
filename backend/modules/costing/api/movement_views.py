from datetime import date
from uuid import UUID

from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.costing.infrastructure.adapters import InventoryCompanyStock
from modules.costing.infrastructure.django.valuation_repository import DjangoValuationStore
from shared.tenancy import company_id_from

REQUIRED_MODULES = ('costing',)

SOURCE_LABELS = {
    'sales_order': 'Pedido de venta',
    'purchase_receipt': 'Recepción de compra',
    'inventory_adjustment': 'Ajuste de inventario',
    'inventory_opening': 'Apertura de existencias',
}
SOURCE_TYPES = set(SOURCE_LABELS)


class ValuationPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError('Fecha inválida: use el formato AAAA-MM-DD.') from None


def _parse_uuid(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError:
        raise ValueError('Valor inválido: use un identificador.') from None


def _parse_source_type(raw: str) -> str:
    if raw not in SOURCE_TYPES:
        raise ValueError('Valor inválido: use una clase de origen conocida.')
    return raw


def _parse_source_id(raw: str) -> str:
    text = raw.strip()
    if not text or len(text) > 64:
        raise ValueError('Valor inválido: use el identificador del documento de origen.')
    return text


def parse_filters(params) -> dict:
    """Convierte los query params en filtros tipados; los valores inválidos dan 400 por parámetro."""
    errors: dict[str, list[str]] = {}
    values: dict[str, object] = {}
    for name, parse in (('date_from', _parse_date), ('date_to', _parse_date), ('product_id', _parse_uuid),
                        ('movement_id', _parse_uuid), ('source_type', _parse_source_type),
                        ('source_id', _parse_source_id)):
        raw = params.get(name)
        if raw is None or raw == '':
            continue
        try:
            values[name] = parse(raw)
        except ValueError as exc:
            errors[name] = [str(exc)]
    if 'source_id' in values and 'source_type' not in values:
        errors['source_id'] = ['Indique también source_type con una clase de origen.']
    if 'date_from' in values and 'date_to' in values and values['date_from'] > values['date_to']:
        errors['date_to'] = ['La fecha final no puede ser anterior a la inicial.']
    if errors:
        raise ValidationError(errors)
    return values


def _text(value) -> str:
    return format(value, 'f')


class MovementValuationListView(APIView):
    """Movimientos valorados de la empresa, de solo lectura, con filtros por producto, origen y fecha."""

    required_modules = REQUIRED_MODULES

    def get(self, request):
        company_id = company_id_from(request)
        queryset = DjangoValuationStore(company_id).list_valuations(**parse_filters(request.query_params))
        paginator = ValuationPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        names = InventoryCompanyStock(company_id).names({row.product_id for row in page})
        return paginator.get_paginated_response([{
            'id': row.id, 'movement_id': str(row.movement_id), 'product_id': str(row.product_id),
            'product_name': names.get(row.product_id, ('', None))[0],
            'unit_abbreviation': names.get(row.product_id, ('', None))[1], 'kind': row.kind,
            'quantity': _text(row.quantity), 'unit_cost': _text(row.unit_cost), 'value': _text(row.value),
            'average_before': _text(row.average_before), 'average_after': _text(row.average_after),
            'cost_origin': row.cost_origin, 'source_type': row.source_type, 'source_id': row.source_id,
            'source_label': SOURCE_LABELS.get(row.source_type or '', 'Reversión' if row.reverses_movement_id
                                              else 'Movimiento manual'),
            'reverses_movement_id': str(row.reverses_movement_id) if row.reverses_movement_id else None,
            'occurred_at': row.occurred_at.isoformat(), 'status': 'valued'} for row in page])


class ProductCostListView(APIView):
    """Costo corriente (cantidad, valor y promedio) por producto."""

    required_modules = REQUIRED_MODULES

    def get(self, request):
        from modules.costing.domain.costing import CostState

        company_id = company_id_from(request)
        rows = list(DjangoValuationStore(company_id).list_costs())
        names = InventoryCompanyStock(company_id).names({row.product_id for row in rows})
        body = [{
            'product_id': str(row.product_id), 'product_name': names.get(row.product_id, ('', None))[0],
            'unit_abbreviation': names.get(row.product_id, ('', None))[1], 'quantity': _text(row.quantity),
            'total_value': _text(row.total_value),
            'average_cost': _text(CostState(row.quantity, row.total_value).average)} for row in rows]
        return Response(sorted(body, key=lambda item: (item['product_name'].lower(), item['product_id'])))
