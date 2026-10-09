from uuid import UUID

from django.db import transaction
from django.db.models import F, QuerySet

from modules.sales.domain.order import Order
from modules.sales.domain.repositories import BY_EXPECTED_DELIVERY, OrderFilters

from .mappers import to_entity, to_item_values, to_order_values, to_payment_model, to_summary
from .models import OrderItemModel, OrderModel, PaymentModel


class OrderSummaryList:
    """Vista perezosa de resúmenes sobre un queryset: permite paginar sin cargar todos los pedidos."""

    def __init__(self, queryset: QuerySet):
        self._queryset = queryset

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [to_summary(model) for model in self._queryset[index]]
        return to_summary(self._queryset[index])

    def __iter__(self):
        return (to_summary(model) for model in self._queryset)


def _detail_queryset() -> QuerySet:
    return OrderModel.objects.prefetch_related('items', 'payments')


class DjangoOrderRepository:
    def get(self, order_id: UUID) -> Order | None:
        model = _detail_queryset().filter(pk=order_id).first()
        return to_entity(model) if model else None

    def get_for_update(self, order_id: UUID) -> Order | None:
        """Bloquea la fila del pedido (exige una transacción abierta); ítems y pagos se leen ya con el bloqueo."""
        locked = OrderModel.objects.select_for_update().filter(pk=order_id).first()
        if locked is None:
            return None
        return self.get(order_id)

    @transaction.atomic
    def save(self, order: Order) -> Order:
        model, _ = OrderModel.objects.update_or_create(id=order.id, defaults=to_order_values(order))
        self._sync_items(order, model)
        self._append_new_payments(order, model)
        return self.get(order.id)

    @staticmethod
    def _sync_items(order: Order, model: OrderModel) -> None:
        kept_ids = {item.id for item in order.items}
        OrderItemModel.objects.filter(order=model).exclude(id__in=kept_ids).delete()
        for item in order.items:
            OrderItemModel.objects.update_or_create(id=item.id, defaults=to_item_values(item, model))

    @staticmethod
    def _append_new_payments(order: Order, model: OrderModel) -> None:
        """Los pagos solo se agregan: nunca se modifican ni se borran los ya registrados."""
        existing = set(PaymentModel.objects.filter(order=model).values_list('id', flat=True))
        new = [to_payment_model(payment, model) for payment in order.payments if payment.id not in existing]
        PaymentModel.objects.bulk_create(new)

    def list(self, filters: OrderFilters) -> OrderSummaryList:
        queryset = OrderModel.objects.all()
        if filters.statuses:
            queryset = queryset.filter(status__in=[s.value for s in filters.statuses])
        if filters.payment_statuses:
            queryset = queryset.filter(payment_status__in=[s.value for s in filters.payment_statuses])
        if filters.sales_channel is not None:
            queryset = queryset.filter(sales_channel=filters.sales_channel.value)
        if filters.customer_id is not None:
            queryset = queryset.filter(customer_id=filters.customer_id)
        if filters.date_from is not None:
            queryset = queryset.filter(**{f'{filters.date_field}__gte': filters.date_from})
        if filters.date_to is not None:
            queryset = queryset.filter(**{f'{filters.date_field}__lte': filters.date_to})
        if filters.has_balance is True:
            queryset = queryset.filter(total__gt=F('paid_total'))
        elif filters.has_balance is False:
            queryset = queryset.filter(total__lte=F('paid_total'))
        if filters.ordering == BY_EXPECTED_DELIVERY:
            queryset = queryset.order_by(F('expected_delivery_date').asc(nulls_last=True), 'order_date', 'id')
        else:
            queryset = queryset.order_by('-order_date', '-created_at', 'id')
        return OrderSummaryList(queryset)

