from rest_framework import serializers

from .stock_serializers import UnitSerializer


class LotSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    status = serializers.ChoiceField(choices=['refrigerating', 'released'])
    lot_date = serializers.DateField()
    fiscal_period_name = serializers.CharField()
    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    product_active = serializers.BooleanField()
    unit = UnitSerializer(allow_null=True)
    warehouse_id = serializers.UUIDField()
    warehouse_name = serializers.CharField()
    physical_quantity = serializers.DecimalField(max_digits=16, decimal_places=4)
    available_quantity = serializers.DecimalField(max_digits=16, decimal_places=4)
    created_at = serializers.DateTimeField(allow_null=True)
    released_at = serializers.DateTimeField(allow_null=True)
    released_by_name = serializers.CharField(allow_blank=True)
