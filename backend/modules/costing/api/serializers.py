from rest_framework import serializers


class AdoptionLineInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    reconciled_quantity = serializers.CharField(allow_blank=True, trim_whitespace=False)
    total_value = serializers.CharField(required=False, allow_null=True, allow_blank=True, trim_whitespace=False)
    declared_zero = serializers.BooleanField(required=False, default=False)
    source = serializers.CharField(required=False, allow_null=True, allow_blank=True, trim_whitespace=False)


class AdoptionInputSerializer(serializers.Serializer):
    adoption_id = serializers.UUIDField()
    lines = AdoptionLineInputSerializer(many=True, allow_empty=True)
