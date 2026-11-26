from rest_framework import serializers


class OrderCreateSerializer(serializers.Serializer):
    recipe_id = serializers.UUIDField()
    warehouse_id = serializers.UUIDField()
    # Se valida en el dominio (entero positivo); aquí solo se acepta el valor tal como llega.
    preparations = serializers.JSONField(required=False, allow_null=True)


class OrderUpdateSerializer(serializers.Serializer):
    warehouse_id = serializers.UUIDField()
    preparations = serializers.JSONField(required=False, allow_null=True)
