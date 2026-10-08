from rest_framework import serializers

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


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class PaymentInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_method = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    payment_date = serializers.DateField(required=False, allow_null=True)
    reference = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# --- Salida ---------------------------------------------------------------------------------------------------


def order_code(order_id) -> str:
    """Etiqueta corta para mostrar; no se persiste ni identifica al pedido (el identificador es el UUID)."""
    return 'P-' + str(order_id).replace('-', '')[:8].upper()


def _money(**extra) -> serializers.DecimalField:
    return serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, **extra)


class _CustomerMixin(serializers.Serializer):
    """`customer` = {id, name} o null; los nombres llegan por contexto (una consulta por lote)."""

    code = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()

    def get_code(self, obj) -> str:
        return order_code(obj.id)

    def get_customer(self, obj):
        if obj.customer_id is None:
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
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


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
