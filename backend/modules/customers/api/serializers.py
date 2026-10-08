from rest_framework import serializers

from modules.customers.domain.customer import NAME_MAX_LENGTH


class CustomerInputSerializer(serializers.Serializer):
    """Valida forma y tipos; las reglas (correo, teléfono, longitudes) las aplica el dominio.

    `active` no es editable aquí. `confirm_duplicate` solo se usa en el alta y no se persiste.
    """

    name = serializers.CharField(max_length=NAME_MAX_LENGTH)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    confirm_duplicate = serializers.BooleanField(required=False, default=False)


class CustomerSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    notes = serializers.CharField(read_only=True)
    active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
