from uuid import UUID

from django.db import transaction

from modules.production.domain.production_order import OrderIngredient, ProductionOrder

from .models import ProductionOrderCounterModel, ProductionOrderIngredientModel, ProductionOrderModel


def to_entity(model: ProductionOrderModel) -> ProductionOrder:
    return ProductionOrder(
        id=model.id, number=model.number, status=model.status, recipe_id=model.recipe_id,
        recipe_name=model.recipe_name, result_product_id=model.result_product_id,
        result_product_name=model.result_product_name, result_unit_id=model.result_unit_id,
        result_unit_abbreviation=model.result_unit_abbreviation,
        yield_per_preparation=model.yield_per_preparation, warehouse_id=model.warehouse_id,
        preparations=model.preparations, started_at=model.started_at, created_at=model.created_at,
        updated_at=model.updated_at,
        ingredients=[OrderIngredient(line.product_id, line.product_name, line.unit_id, line.unit_abbreviation,
                                     line.quantity_per_preparation) for line in model.ingredients.all()])


class OrderList:
    def __init__(self, queryset):
        self.queryset = queryset

    def count(self):
        return self.queryset.count()

    def __len__(self):
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [to_entity(model) for model in self.queryset[index]]
        return to_entity(self.queryset[index])


class DjangoProductionOrderRepository:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _orders(self):
        return ProductionOrderModel.objects.filter(company_id=self.company_id).prefetch_related('ingredients')

    def get(self, order_id: UUID, *, for_update: bool = False) -> ProductionOrder | None:
        if for_update:
            ProductionOrderModel.objects.select_for_update().filter(company_id=self.company_id, pk=order_id).first()
        model = self._orders().filter(pk=order_id).first()
        return to_entity(model) if model else None

    def _next_number(self) -> int:
        counter, _ = ProductionOrderCounterModel.objects.select_for_update().get_or_create(
            company_id=self.company_id)
        counter.last_number += 1
        counter.save(update_fields=['last_number'])
        return counter.last_number

    def save(self, order: ProductionOrder) -> ProductionOrder:
        with transaction.atomic():
            model = ProductionOrderModel.objects.filter(company_id=self.company_id, pk=order.id).first()
            if model is None:
                model = ProductionOrderModel(
                    id=order.id, company_id=self.company_id, number=self._next_number(), recipe_id=order.recipe_id,
                    recipe_name=order.recipe_name, result_product_id=order.result_product_id,
                    result_product_name=order.result_product_name, result_unit_id=order.result_unit_id,
                    result_unit_abbreviation=order.result_unit_abbreviation,
                    yield_per_preparation=order.yield_per_preparation)
                created = True
            else:
                created = False
            model.warehouse_id = order.warehouse_id
            model.preparations = order.preparations
            model.status = order.status
            model.started_at = order.started_at
            model.save()
            if created:
                ProductionOrderIngredientModel.objects.bulk_create([
                    ProductionOrderIngredientModel(
                        order=model, product_id=line.product_id, product_name=line.product_name,
                        unit_id=line.unit_id, unit_abbreviation=line.unit_abbreviation,
                        quantity_per_preparation=line.quantity_per_preparation, position=position)
                    for position, line in enumerate(order.ingredients)])
        return to_entity(self._orders().get(pk=order.id))

    def list(self, *, status: str = 'all') -> OrderList:
        queryset = self._orders().order_by('-number')
        if status != 'all':
            queryset = queryset.filter(status=status)
        return OrderList(queryset)
