from modules.sales.domain.enums import OrderStatus, PaymentMethod, PaymentStatus, SalesChannel
from modules.sales.domain.order import Order, OrderItem, Payment
from modules.sales.domain.repositories import OrderSummary

from .models import OrderModel, PaymentModel


def to_entity(model: OrderModel) -> Order:
    """Reconstruye el agregado; los importes derivados se recalculan desde los ítems y pagos, no se leen."""
    return Order(
        id=model.id,
        customer_id=model.customer_id,
        sales_channel=SalesChannel(model.sales_channel),
        order_date=model.order_date,
        expected_delivery_date=model.expected_delivery_date,
        delivered_date=model.delivered_date,
        notes=model.notes,
        discount=model.discount,
        status=OrderStatus(model.status),
        cancellation_reason=model.cancellation_reason,
        cancelled_at=model.cancelled_at,
        items=[
            OrderItem(id=item.id, product_id=item.product_id, product_name=item.product_name,
                      unit_price=item.unit_price, quantity=item.quantity)
            for item in model.items.all()
        ],
        payments=[
            Payment(id=payment.id, amount=payment.amount, payment_method=PaymentMethod(payment.payment_method),
                    payment_date=payment.payment_date, reference=payment.reference, created_at=payment.created_at)
            for payment in model.payments.all()
        ],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def to_summary(model: OrderModel) -> OrderSummary:
    return OrderSummary(
        id=model.id,
        customer_id=model.customer_id,
        sales_channel=SalesChannel(model.sales_channel),
        order_date=model.order_date,
        expected_delivery_date=model.expected_delivery_date,
        status=OrderStatus(model.status),
        payment_status=PaymentStatus(model.payment_status),
        total=model.total,
        paid_total=model.paid_total,
    )


def to_order_values(order: Order) -> dict[str, object]:
    return {
        'customer_id': order.customer_id,
        'status': order.status.value,
        'sales_channel': order.sales_channel.value,
        'order_date': order.order_date,
        'expected_delivery_date': order.expected_delivery_date,
        'delivered_date': order.delivered_date,
        'notes': order.notes,
        'cancellation_reason': order.cancellation_reason,
        'cancelled_at': order.cancelled_at,
        'subtotal': order.subtotal,
        'discount': order.discount,
        'total': order.total,
        'paid_total': order.paid_total,
        'payment_status': order.payment_status.value,
    }


def to_item_values(item: OrderItem, order_model: OrderModel) -> dict[str, object]:
    return {
        'order': order_model,
        'product_id': item.product_id,
        'product_name': item.product_name,
        'unit_price': item.unit_price,
        'quantity': item.quantity,
        'subtotal': item.subtotal,
    }


def to_payment_model(payment: Payment, order_model: OrderModel) -> PaymentModel:
    return PaymentModel(id=payment.id, order=order_model, amount=payment.amount,
                        payment_method=payment.payment_method.value, payment_date=payment.payment_date,
                        reference=payment.reference)

