from rest_framework import serializers


class QuantityField(serializers.DecimalField):
    def to_internal_value(self, data):
        if isinstance(data, (float, bool)):
            raise serializers.ValidationError('Envía la cantidad como texto decimal.')
        return super().to_internal_value(data)


class IngredientInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    unit_id = serializers.UUIDField(allow_null=True, required=False)
    quantity = QuantityField(max_digits=14, decimal_places=4)


class RecipeInputSerializer(serializers.Serializer):
    name = serializers.CharField(allow_blank=True, max_length=150)
    result_product_id = serializers.UUIDField()
    yield_quantity = QuantityField(max_digits=14, decimal_places=4)
    ingredients = IngredientInputSerializer(many=True, allow_empty=True)
