from rest_framework import serializers

from modules.inventory.domain.warehouse import NAME_MAX_LENGTH


class WarehouseInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH)
    description = serializers.CharField(required=False, allow_blank=True)
    is_default = serializers.BooleanField(required=False)


class WarehouseSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    active = serializers.BooleanField(read_only=True)
    is_default = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
