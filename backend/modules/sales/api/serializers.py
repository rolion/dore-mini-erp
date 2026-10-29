from decimal import Decimal

from rest_framework import serializers

from modules.sales.domain.order import order_code

QUANTITY_PLACES = Decimal('0.0001')

# --- Entrada: solo forma y tipos. Las reglas (obligatoriedad, rangos, estados) las aplica el dominio, que junta ---
# --- los errores de todos los campos. Los campos derivados y de estado no se aceptan y se ignoran. -------------


class OrderInputSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    sales_channel = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    order_date = serializers.DateField(required=False, allow_null=True)
    expected_delivery_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField()


class OrderItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField()


class DiscountSerializer(serializers.Serializer):
    discount = serializers.DecimalField(max_digits=12, decimal_places=2)


class DeliverSerializer(serializers.Serializer):
    delivered_date = serializers.DateField(required=False, allow_null=True)
    warehouse_id = serializers.UUIDField(required=False, allow_null=True)


class DeliveryPreviewQuerySerializer(serializers.Serializer):
    warehouse_id = serializers.UUIDField(required=False, allow_null=True)


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class PaymentInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_method = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    payment_date = serializers.DateField(required=False, allow_null=True)
    reference = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# --- Salida ---------------------------------------------------------------------------------------------------


def _money(**extra) -> serializers.DecimalField:
    return serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, **extra)


class _CustomerMixin(serializers.Serializer):
    """`customer` = {id, name} o null; los nombres llegan por contexto (una consulta por lote)."""

    code = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()

    def get_code(self, obj) -> str:
        return order_code(obj.id)

    def get_customer(self, obj):
        if obj.customer_id is None or not self.context.get('customers_available', True):
            return None
        name = self.context.get('customer_names', {}).get(obj.customer_id, '')
        return {'id': obj.customer_id, 'name': name}


class OrderItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    product_id = serializers.UUIDField(read_only=True)
    product_name = serializers.CharField(read_only=True)
    unit_price = _money()
    quantity = serializers.IntegerField(read_only=True)
    subtotal = _money()


class PaymentSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    amount = _money()
    payment_method = serializers.CharField(source='payment_method.value', read_only=True)
    payment_date = serializers.DateField(read_only=True)
    reference = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class OrderSerializer(_CustomerMixin):
    id = serializers.UUIDField(read_only=True)
    sales_channel = serializers.CharField(source='sales_channel.value', read_only=True)
    order_date = serializers.DateField(read_only=True)
    expected_delivery_date = serializers.DateField(read_only=True)
    delivered_date = serializers.DateField(read_only=True)
    notes = serializers.CharField(read_only=True)
    status = serializers.CharField(source='status.value', read_only=True)
    payment_status = serializers.CharField(source='payment_status.value', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    subtotal = _money()
    discount = _money()
    total = _money()
    paid_total = _money()
    balance = _money()
    payments = PaymentSerializer(many=True, read_only=True)
    cancellation_reason = serializers.CharField(read_only=True)
    cancelled_at = serializers.DateTimeField(read_only=True)
    editable = serializers.BooleanField(read_only=True)
    allowed_transitions = serializers.ListField(child=serializers.CharField(), read_only=True)
    can_register_payment = serializers.BooleanField(read_only=True)
    stock_output = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_stock_output(self, obj):
        """Salida de inventario del pedido entregado (`null` si no hubo o Inventario está deshabilitado)."""
        return stock_output_data(self.context.get('stock_output'))


def quantity_text(value) -> str:
    """Cantidad con la precisión del libro de movimientos (4 decimales)."""
    return format(value.quantize(QUANTITY_PLACES), 'f')


def stock_output_data(record) -> dict | None:
    if record is None:
        return None
    return {
        'reference': record.reference,
        'warehouse': {'id': str(record.warehouse_id), 'name': record.warehouse_name},
        'occurred_at': serializers.DateTimeField().to_representation(record.occurred_at),
        'user_name': record.user_name,
        'movements': [{
            'id': str(m.id),
            'product': {'id': str(m.product_id), 'name': m.product_name},
            'quantity': quantity_text(m.quantity),
            'unit': {'abbreviation': m.unit},
        } for m in record.movements],
    }


def delivery_preview_data(preview) -> dict:
    return {
        'inventory_enabled': preview.inventory_enabled,
        'requires_stock_output': preview.requires_stock_output,
        'allow_negative_stock': preview.allow_negative_stock,
        'warehouses': [{'id': str(w.id), 'name': w.name, 'is_default': w.is_default} for w in preview.warehouses],
        'warehouse_id': str(preview.warehouse_id) if preview.warehouse_id else None,
        'lines': [{
            'product': {'id': str(line.product.id), 'name': line.product.name},
            'quantity': quantity_text(line.quantity),
            'unit': {'abbreviation': line.product.unit},
            'available': None if line.available is None else quantity_text(line.available),
            'projected': None if line.projected is None else quantity_text(line.projected),
            'insufficient': line.insufficient,
        } for line in preview.lines],
    }


class OrderSummarySerializer(_CustomerMixin):
    id = serializers.UUIDField(read_only=True)
    sales_channel = serializers.CharField(source='sales_channel.value', read_only=True)
    order_date = serializers.DateField(read_only=True)
    expected_delivery_date = serializers.DateField(read_only=True)
    status = serializers.CharField(source='status.value', read_only=True)
    payment_status = serializers.CharField(source='payment_status.value', read_only=True)
    total = _money()
    paid_total = _money()
    balance = _money()
