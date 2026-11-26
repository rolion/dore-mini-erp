import uuid

from django.db import models
from django.db.models import Q


class OrderModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Empresa propietaria; solo UUID, sin FK. Ítems y pagos heredan la empresa de su pedido.
    company_id = models.UUIDField(db_index=True)
    # Referencias a otros módulos solo por UUID, sin FK (los módulos no acoplan modelos ni migraciones).
    customer_id = models.UUIDField(null=True, blank=True, db_index=True)
    # Almacén de Inventario desde el que se atiende el pedido; nulo en pedidos anteriores.
    warehouse_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(max_length=20, db_index=True)
    sales_channel = models.CharField(max_length=20, db_index=True)
    order_date = models.DateField(db_index=True)
    expected_delivery_date = models.DateField(null=True, blank=True, db_index=True)
    delivered_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    cancellation_reason = models.TextField(blank=True, default='')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by_name = models.CharField(max_length=255, blank=True, default='')
    # Devolución total (pedido entregado) y reembolso externo declarado.
    returned_at = models.DateTimeField(null=True, blank=True)
    returned_by_name = models.CharField(max_length=255, blank=True, default='')
    return_reason = models.TextField(blank=True, default='')
    refund_acknowledged = models.BooleanField(default=False)
    # Número correlativo de la serie de ventas por período fiscal: se asigna al confirmar y no cambia (ver ADR).
    # `fiscal_period_id` es solo UUID, sin FK (el período es de Contabilidad); el nombre es una instantánea.
    fiscal_period_id = models.UUIDField(null=True, blank=True)
    fiscal_period_name = models.CharField(max_length=80, blank=True, default='')
    number = models.PositiveIntegerField(null=True, blank=True)
    # Derivados: solo los escribe el repositorio a partir del agregado (permiten filtrar y paginar en SQL).
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sales_order'
        ordering = ['-order_date', '-created_at', 'id']
        constraints = [
            models.CheckConstraint(condition=Q(discount__gte=0), name='sales_order_discount_gte_0'),
            models.CheckConstraint(condition=Q(total__gte=0), name='sales_order_total_gte_0'),
            models.CheckConstraint(condition=Q(paid_total__gte=0), name='sales_order_paid_total_gte_0'),
            models.CheckConstraint(condition=Q(number__isnull=True) | Q(number__gt=0), name='sales_order_number_gt_0'),
            models.CheckConstraint(
                condition=(Q(number__isnull=True, fiscal_period_id__isnull=True)
                           | Q(number__isnull=False, fiscal_period_id__isnull=False)),
                name='sales_order_number_with_period'),
            models.UniqueConstraint(fields=['company_id', 'fiscal_period_id', 'number'],
                                    condition=Q(number__isnull=False), name='sales_order_number_unique'),
        ]


class OrderItemModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(OrderModel, on_delete=models.CASCADE, related_name='items')
    product_id = models.UUIDField()
    product_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_order_item'
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['order', 'product_id'], name='sales_item_unique_product_per_order'),
            models.CheckConstraint(condition=Q(quantity__gt=0), name='sales_item_quantity_gt_0'),
        ]


class PaymentModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(OrderModel, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20)
    payment_date = models.DateField()
    reference = models.CharField(max_length=100, blank=True, default='')
    # Idempotencia: el mismo intento de cobro (clave + huella) no crea otro pago en el pedido.
    idempotency_key = models.UUIDField(null=True, blank=True)
    request_digest = models.CharField(max_length=64, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_payment'
        ordering = ['created_at', 'id']
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='sales_payment_amount_gt_0'),
            models.UniqueConstraint(fields=['order', 'idempotency_key'], condition=Q(idempotency_key__isnull=False),
                                    name='sales_payment_order_key_unique'),
        ]


class OrderNumberCounterModel(models.Model):
    """Último número asignado de la serie de ventas de una empresa en un período fiscal."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    fiscal_period_id = models.UUIDField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'sales_order_number_counter'
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'fiscal_period_id'], name='sales_order_counter_unique'),
        ]
