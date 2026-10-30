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
    quantity = serializers.DecimalField(max_digits=16, decimal_places=4)
    movement_id = serializers.UUIDField(allow_null=True)


class OpeningSerializer(serializers.Serializer):
    opening_id = serializers.UUIDField()
    warehouse_id = serializers.UUIDField()
    movement_date = serializers.DateField()
    reference = serializers.CharField()
    lines = OpeningLineSerializer(many=True)


class UnitSerializer(serializers.Serializer):
    abbreviation = serializers.CharField()
    allows_fractions = serializers.BooleanField()


class StockBalanceSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    product_active = serializers.BooleanField()
    warehouse_id = serializers.UUIDField()
    warehouse_name = serializers.CharField()
    warehouse_active = serializers.BooleanField()
    category = serializers.CharField(allow_null=True)
    can_buy = serializers.BooleanField()
    can_sell = serializers.BooleanField()
    quantity = serializers.DecimalField(max_digits=16, decimal_places=4)
    balance_state = serializers.ChoiceField(choices=['zero', 'positive', 'negative'])
    unit = UnitSerializer(allow_null=True)


class StockPositionSerializer(StockBalanceSerializer):
    has_history = serializers.BooleanField()
    can_register_opening = serializers.BooleanField()
    can_register_adjustment = serializers.BooleanField()
