from rest_framework import serializers


class PriceField(serializers.DecimalField):
    def to_internal_value(self, data):
        if isinstance(data, (float, bool)):
            raise serializers.ValidationError('Envía el precio como texto decimal.')
        return super().to_internal_value(data)


class MinutesField(serializers.IntegerField):
    def to_internal_value(self, data):
        if isinstance(data, bool):
            raise serializers.ValidationError('Ingresa minutos enteros mayores que cero.')
        return super().to_internal_value(data)


class ServiceInputSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    code = serializers.CharField(required=False, allow_blank=True, max_length=50)
    description = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    base_price = PriceField(required=False, max_digits=12, decimal_places=2, min_value=0)
    duration_minutes = MinutesField(required=False, min_value=1, max_value=2147483647)
    specialty_id = serializers.UUIDField(required=False, allow_null=True)


class ServiceSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    base_price = serializers.DecimalField(read_only=True, max_digits=12, decimal_places=2)
    duration_minutes = serializers.IntegerField(read_only=True)
    specialty_id = serializers.UUIDField(read_only=True, allow_null=True)
    specialty_name = serializers.SerializerMethodField()
    active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_specialty_name(self, service):
        return self.context.get('specialty_names', {}).get(service.specialty_id)
