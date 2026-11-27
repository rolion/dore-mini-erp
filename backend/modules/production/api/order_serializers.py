from rest_framework import serializers


class OrderCreateSerializer(serializers.Serializer):
    recipe_id = serializers.UUIDField()
    warehouse_id = serializers.UUIDField()
    # Se valida en el dominio (entero positivo); aquí solo se acepta el valor tal como llega.
    preparations = serializers.JSONField(required=False, allow_null=True)


class OrderUpdateSerializer(serializers.Serializer):
    warehouse_id = serializers.UUIDField()
    preparations = serializers.JSONField(required=False, allow_null=True)


class RefrigerationIngredientSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    # Cantidad tal como llega; el dominio la valida (número, decimales, signo).
    actual_quantity = serializers.JSONField(required=False, allow_null=True)


class OrderRefrigerateSerializer(serializers.Serializer):
    entered_at = serializers.DateTimeField()
    actual_output = serializers.JSONField(required=False, allow_null=True)
    ingredients = RefrigerationIngredientSerializer(many=True)


class OrderPackSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    # Se valida en el dominio (entero positivo); aquí solo se acepta el valor tal como llega.
    packs = serializers.JSONField(required=False, allow_null=True)
    pack_product_id = serializers.UUIDField()
    bag_product_id = serializers.UUIDField()
    # Se valida en el dominio (positiva, hasta 4 decimales); aquí solo se acepta el valor tal como llega.
    bag_per_pack = serializers.JSONField(required=False, allow_null=True)
    label_product_id = serializers.UUIDField(required=False, allow_null=True)
