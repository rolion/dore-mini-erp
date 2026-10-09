from rest_framework import serializers

# --- Entrada: solo forma y tipos. Las reglas (obligatoriedad, rangos, estados) las aplica el dominio, que junta ---
# --- los errores de todos los campos. Los campos de estado y auditoría no se aceptan y se ignoran. --------------


class ExpenseInputSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    expense_date = serializers.DateField(required=False, allow_null=True)
    payment_method = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    supplier_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CategoryInputSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# --- Salida ---------------------------------------------------------------------------------------------------


class CategorySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class _CategoryRefSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    active = serializers.BooleanField(read_only=True)


class ExpenseSummarySerializer(serializers.Serializer):
    """Forma de la lista; la categoría llega por contexto (`categories`, una consulta por lote)."""

    id = serializers.UUIDField(read_only=True)
    description = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    expense_date = serializers.DateField(read_only=True)
    category = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    supplier_name = serializers.CharField(read_only=True)
    status = serializers.SerializerMethodField()
    voided_at = serializers.DateTimeField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_category(self, obj):
        category = self.context.get('categories', {}).get(obj.category_id)
        if category is None:
            return {'id': obj.category_id, 'name': '', 'active': False}
        return _CategoryRefSerializer(category).data

    def get_payment_method(self, obj) -> str:
        return obj.payment_method.value

    def get_status(self, obj) -> str:
        return obj.status.value


class ExpenseSerializer(ExpenseSummarySerializer):
    notes = serializers.CharField(read_only=True)
