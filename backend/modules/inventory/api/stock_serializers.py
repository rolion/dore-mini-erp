from decimal import Decimal

from rest_framework import serializers

from modules.inventory.domain.stock import REFERENCE_MAX_LENGTH


class RawQuantityField(serializers.Field):
    """Entrega la cantidad al dominio tal cual (un float JSON pasa por su texto); el dominio la valida en español."""

    def to_internal_value(self, data):
        if isinstance(data, float):
            return Decimal(str(data))
        if isinstance(data, bool) or not isinstance(data, (int, str)):
            raise serializers.ValidationError('La cantidad debe ser un número decimal.')
        return data


class OpeningLineInputSerializer(serializers.Serializer):
    """Valida forma y tipos; las reglas de negocio las aplica el dominio."""

    product_id = serializers.UUIDField()
    quantity = RawQuantityField()


class OpeningInputSerializer(serializers.Serializer):
    opening_id = serializers.UUIDField()
    warehouse_id = serializers.UUIDField()
    movement_date = serializers.DateField()
    reference = serializers.CharField(max_length=REFERENCE_MAX_LENGTH)
    lines = OpeningLineInputSerializer(many=True, allow_empty=True)


class OpeningLineSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    movement_id = serializers.UUIDField()


class OpeningSerializer(serializers.Serializer):
    opening_id = serializers.UUIDField()
    warehouse_id = serializers.UUIDField()
    movement_date = serializers.DateField()
    reference = serializers.CharField()
    lines = OpeningLineSerializer(many=True)


class UnitSerializer(serializers.Serializer):
    name = serializers.CharField()
    abbreviation = serializers.CharField()
    allows_fractions = serializers.BooleanField()


class StockBalanceSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    product_name = serializers.CharField(allow_null=True)
    warehouse_id = serializers.UUIDField()
    warehouse_name = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    unit = UnitSerializer(allow_null=True)


class StockMovementSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    movement_type = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    movement_date = serializers.DateField()
    reference = serializers.CharField()
    created_at = serializers.DateTimeField()
