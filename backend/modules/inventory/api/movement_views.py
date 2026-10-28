from uuid import UUID

from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.inventory.application.movement_use_cases import GetMovement, ListMovements
from modules.inventory.domain.exceptions import MovementNotFound
from modules.inventory.domain.movement import SOURCE_TYPES, MovementKind, StockMovement
from modules.inventory.infrastructure.adapters import CatalogProductDirectory
from modules.inventory.infrastructure.django.movement_repository import DjangoStockMovementRepository
from modules.inventory.infrastructure.django.repositories import DjangoWarehouseRepository
from shared import module_gate
from shared.tenancy import company_id_from

from .movement_filters import parse_movement_filters
from .pagination import WarehousePagination

MOVEMENT_NOT_FOUND = 'Movimiento no encontrado.'


class MovementPagination(WarehousePagination):
    page_size = 25


def _decimal(value) -> str:
    return format(value, 'f')


class MovementPresenter:
    """Arma la representación de lectura: nombres de producto y almacén, unidad y origen (una consulta por tipo)."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self.warehouses = {w.id: w.name for w in DjangoWarehouseRepository(company_id).list()}
        self._enabled = module_gate.enabled_keys(company_id)
        self._products: dict = {}

    def load_products(self, movements: list[StockMovement]) -> None:
        ids = {m.product_id for m in movements}
        self._products = CatalogProductDirectory(self.company_id).get_products(ids)

    def present(self, movement: StockMovement, *, detail: bool = False) -> dict:
        product = self._products.get(movement.product_id)
        data = {
            'id': movement.id,
            'occurred_at': movement.occurred_at,
            'reference': movement.reference,
            'product': {'id': movement.product_id, 'name': product.name if product else ''},
            'warehouse': {'id': movement.warehouse_id, 'name': self.warehouses.get(movement.warehouse_id, '')},
            'kind': movement.kind.value,
            'quantity_in': _decimal(movement.quantity) if movement.kind is MovementKind.IN else None,
            'quantity_out': _decimal(movement.quantity) if movement.kind is MovementKind.OUT else None,
            'unit': {'abbreviation': product.unit_abbreviation if product else None},
            'status': movement.status.value,
            'source': self._source(movement),
        }
        if detail:
            data.update({
                'quantity': _decimal(movement.quantity),
                'reason': movement.reason,
                'user': {'id': movement.user_id, 'name': movement.user_name},
                'reversed_by': {'id': movement.reversed_by_id} if movement.reversed_by_id else None,
                'reverses': {'id': movement.reverses_id} if movement.reverses_id else None,
                'created_at': movement.created_at,
            })
        return data

    def _source(self, movement: StockMovement) -> dict | None:
        if movement.source is None:
            return None
        definition = SOURCE_TYPES[movement.source.type]
        return {
            'type': definition.key, 'label': definition.label, 'id': movement.source.id,
            'line': movement.source.line, 'reference': movement.reference,
            'available': definition.module in self._enabled,
        }


class StockMovementListView(APIView):
    """Libro de movimientos: solo lectura (POST/PATCH/DELETE responden 405)."""

    required_modules = ('inventory',)

    def get(self, request):
        company_id = company_id_from(request)
        filters = parse_movement_filters(request.query_params)
        movements = ListMovements(DjangoStockMovementRepository(company_id)).execute(filters)
        paginator = MovementPagination()
        page = paginator.paginate_queryset(movements, request, view=self)
        presenter = MovementPresenter(company_id)
        presenter.load_products(page)
        return paginator.get_paginated_response([presenter.present(m) for m in page])


class StockMovementDetailView(APIView):
    required_modules = ('inventory',)

    def get(self, request, movement_id):
        company_id = company_id_from(request)
        try:
            movement = GetMovement(DjangoStockMovementRepository(company_id)).execute(movement_id)
        except MovementNotFound as exc:
            raise NotFound(MOVEMENT_NOT_FOUND) from exc
        presenter = MovementPresenter(company_id)
        presenter.load_products([movement])
        return Response(presenter.present(movement, detail=True))
