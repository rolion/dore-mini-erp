from rest_framework import serializers

from modules.catalog.domain.product import NAME_MAX_LENGTH


class ProductInputSerializer(serializers.Serializer):
    """Valida forma y tipos; las reglas de negocio las aplica el dominio. `active` no es editable aquí."""

    name = serializers.CharField(max_length=NAME_MAX_LENGTH)
    description = serializers.CharField(required=False, allow_blank=True)
    sale_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


class ProductSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    sale_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
