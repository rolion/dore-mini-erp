from uuid import UUID

from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.inventory.application.movement_use_cases import GetMovement, ListMovements, ReverseMovement
from modules.inventory.domain.exceptions import (
    InsufficientStock,
    MovementConflict,
    MovementNotFound,
    MovementValidationError,
)
from modules.inventory.domain.movement import SOURCE_TYPES, MovementKind, StockMovement, reversal_block
from modules.inventory.infrastructure.adapters import CatalogProductDirectory, ModularityInventoryPolicy
from modules.inventory.infrastructure.django.movement_repository import DjangoStockMovementRepository
from modules.inventory.infrastructure.django.repositories import DjangoWarehouseRepository
from shared import module_gate
from shared.tenancy import company_id_from

from .insufficient_stock import InsufficientStockConflict
from .movement_filters import parse_movement_filters
from .pagination import WarehousePagination
from .views import Conflict

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

    def present(self, movement: StockMovement, *, detail: bool = False,
                counter: StockMovement | None = None) -> dict:
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
                'reversed_by': self._reversed_by(movement, counter),
                'reversal': self._reversal(movement),
                'reverses': {'id': movement.reverses_id} if movement.reverses_id else None,
                'created_at': movement.created_at,
            })
        return data

    @staticmethod
    def _reversed_by(movement: StockMovement, counter: StockMovement | None) -> dict | None:
        if not movement.reversed_by_id:
            return None
        data: dict = {'id': movement.reversed_by_id}
        if counter is not None:
            data.update({
                'reference': counter.reference, 'occurred_at': counter.occurred_at, 'reason': counter.reason,
                'user': {'id': counter.user_id, 'name': counter.user_name},
            })
        return data

    @staticmethod
    def _reversal(movement: StockMovement) -> dict:
        block = reversal_block(movement)
        return {'allowed': block is None, 'code': block[0] if block else None,
                'message': block[1] if block else None}

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


def _detail_response(company_id: UUID, movement: StockMovement) -> dict:
    counter = None
    if movement.reversed_by_id:
        counter = DjangoStockMovementRepository(company_id).get(movement.reversed_by_id)
    presenter = MovementPresenter(company_id)
    presenter.load_products([movement])
    return presenter.present(movement, detail=True, counter=counter)


class StockMovementDetailView(APIView):
    required_modules = ('inventory',)

    def get(self, request, movement_id):
        company_id = company_id_from(request)
        try:
            movement = GetMovement(DjangoStockMovementRepository(company_id)).execute(movement_id)
        except MovementNotFound as exc:
            raise NotFound(MOVEMENT_NOT_FOUND) from exc
        return Response(_detail_response(company_id, movement))


class ReverseInputSerializer(serializers.Serializer):
    """Valida forma y tipos; el motivo obligatorio y su largo los aplica el dominio."""

    reason = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False, max_length=2000)


class StockMovementReverseView(APIView):
    """Revierte un movimiento manual (sin origen, ajuste o apertura) con un contramovimiento vinculado."""

    required_modules = ('inventory',)

    def post(self, request, movement_id):
        serializer = ReverseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company_id = company_id_from(request)
        user = request.user
        use_case = ReverseMovement(DjangoStockMovementRepository(company_id), ModularityInventoryPolicy(company_id))
        try:
            counter = use_case.execute(
                movement_id, user_id=user.pk, user_name=user.get_full_name().strip() or user.get_username(),
                reason=serializer.validated_data.get('reason', ''), manual_only=True)
        except MovementNotFound as exc:
            raise NotFound(MOVEMENT_NOT_FOUND) from exc
        except MovementValidationError as exc:
            raise ValidationError(exc.errors) from exc
        except InsufficientStock as exc:
            raise InsufficientStockConflict(exc, company_id) from exc
        except MovementConflict as exc:
            raise Conflict(str(exc), exc.code) from exc
        return Response(_detail_response(company_id, counter))
