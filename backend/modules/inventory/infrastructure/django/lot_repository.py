from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from django.db.models import Case, DecimalField, F, QuerySet, Sum, When
from django.db.models.functions import Coalesce

from modules.inventory.domain.lot import LotNumber, LotPosition, LotStatus, StockLot
from modules.inventory.domain.repositories import LotFilters

from .models import StockLotModel

ZERO = Decimal('0')
_DECIMAL = DecimalField(max_digits=16, decimal_places=4)


def to_entity(model: StockLotModel) -> StockLot:
    return StockLot(
        id=model.id, product_id=model.product_id, warehouse_id=model.warehouse_id, lot_date=model.lot_date,
        number=LotNumber(model.fiscal_period_id, model.fiscal_period_name, model.number),
        status=LotStatus(model.status), released_at=model.released_at, released_by_id=model.released_by_id,
        released_by_name=model.released_by_name, created_at=model.created_at)


def _position(model: StockLotModel) -> LotPosition:
    return LotPosition(to_entity(model), model.warehouse.name, model.physical)


class LotList:
    """Lotes con su saldo físico (paginable: cuenta y corta sobre la consulta, sin cargar todo)."""

    def __init__(self, queryset: QuerySet):
        self._queryset = queryset

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [_position(model) for model in self._queryset[index]]
        return _position(self._queryset[index])

    def __iter__(self):
        return (_position(model) for model in self._queryset)


class DjangoStockLotRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _lots(self) -> QuerySet:
        """Lotes de la empresa con su saldo físico (entradas menos salidas de sus movimientos) en una consulta."""
        physical = Sum(Case(When(movements__kind='in', then=F('movements__quantity')),
                            When(movements__kind='out', then=-F('movements__quantity')),
                            output_field=_DECIMAL))
        return (StockLotModel.objects.filter(company_id=self.company_id).select_related('warehouse')
                .annotate(physical=Coalesce(physical, ZERO, output_field=_DECIMAL)))

    def get(self, lot_id: UUID) -> StockLot | None:
        model = StockLotModel.objects.filter(company_id=self.company_id, pk=lot_id).first()
        return to_entity(model) if model else None

    def get_position(self, lot_id: UUID) -> LotPosition | None:
        model = self._lots().filter(pk=lot_id).first()
        return _position(model) if model else None

    def insert(self, lot: StockLot) -> StockLot:
        StockLotModel.objects.create(
            id=lot.id, company_id=self.company_id, product_id=lot.product_id, warehouse_id=lot.warehouse_id,
            code=lot.code, fiscal_period_id=lot.number.period_id, fiscal_period_name=lot.number.period_name,
            number=lot.number.number, lot_date=lot.lot_date, status=lot.status.value)
        return self.get(lot.id)

    def save_release(self, lot: StockLot) -> None:
        StockLotModel.objects.filter(company_id=self.company_id, pk=lot.id).update(
            status=lot.status.value, released_at=lot.released_at, released_by_id=lot.released_by_id,
            released_by_name=lot.released_by_name)

    def list(self, filters: LotFilters) -> LotList:
        queryset = self._lots().order_by('-lot_date', '-number', 'id')
        if filters.search:
            queryset = queryset.filter(code__icontains=filters.search)
        if filters.product_id:
            queryset = queryset.filter(product_id=filters.product_id)
        if filters.warehouse_id:
            queryset = queryset.filter(warehouse_id=filters.warehouse_id)
        if filters.status:
            queryset = queryset.filter(status=filters.status.value)
        if filters.with_stock:
            queryset = queryset.exclude(physical=0)
        return LotList(queryset)

    def for_product(self, product_id: UUID, warehouse_id: UUID) -> Sequence[LotPosition]:
        return list(LotList(self._lots().filter(product_id=product_id, warehouse_id=warehouse_id)
                            .order_by('-lot_date', '-number', 'id')))

    def pairs_with_lots(self) -> set[tuple[UUID, UUID]]:
        rows = StockLotModel.objects.filter(company_id=self.company_id).values_list('product_id', 'warehouse_id')
        return set(rows.order_by().distinct())
