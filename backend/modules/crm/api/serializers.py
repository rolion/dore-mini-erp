from rest_framework import serializers


class CrmCustomerSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    display_name = serializers.CharField()
    phone = serializers.CharField()
    last_purchase_at = serializers.DateField(allow_null=True)
    order_count = serializers.IntegerField()
    outstanding_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField()
