from uuid import UUID

from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from modules.crm.application.queries import ListCrmCustomers, WarehouseFilterUnavailable, WarehouseNotFound
from modules.crm.infrastructure.adapters import (
    CustomerDirectoryAdapter,
    ModuleAvailabilityAdapter,
    SalesReaderAdapter,
    WarehouseDirectoryAdapter,
)
from shared.tenancy import company_id_from

from .pagination import CrmCustomerPagination
from .serializers import CrmCustomerSerializer


def _parse_warehouse(raw: str | None) -> UUID | None:
    if raw is None or raw == '':
        return None
    try:
        return UUID(raw)
    except ValueError as exc:
        raise ValidationError({'warehouse_id': ['Identificador de sucursal inválido.']}) from exc


class CrmCustomerListView(APIView):
    """Listado CRM de solo lectura de la empresa del usuario autenticado (nunca de un dato enviado por el cliente)."""

    required_modules = ('customers',)

    def get(self, request):
        company_id = company_id_from(request)
        warehouse_id = _parse_warehouse(request.query_params.get('warehouse_id'))
        use_case = ListCrmCustomers(
            CustomerDirectoryAdapter(company_id), SalesReaderAdapter(company_id),
            WarehouseDirectoryAdapter(company_id), ModuleAvailabilityAdapter(company_id))
        try:
            listing = use_case.execute(search=request.query_params.get('search', '').strip() or None,
                                       warehouse_id=warehouse_id)
        except WarehouseFilterUnavailable as exc:
            raise ValidationError({'warehouse_id': ['El filtro de sucursal no está disponible.']}) from exc
        except WarehouseNotFound as exc:
            raise ValidationError({'warehouse_id': ['Sucursal no encontrada.']}) from exc
        paginator = CrmCustomerPagination()
        paginator.meta = {'sales_enabled': listing.sales_enabled,
                          'warehouse_filter_enabled': listing.warehouse_filter_enabled}
        page = paginator.paginate_queryset(listing.rows, request, view=self)
        return paginator.get_paginated_response(CrmCustomerSerializer(page, many=True).data)
