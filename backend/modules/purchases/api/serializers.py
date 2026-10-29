from rest_framework import serializers


class SupplierInputSerializer(serializers.Serializer):
    """Valida forma y tipos; las reglas (obligatoriedad, correo, longitudes) las aplica el dominio.

    `active` no es editable aquí.
    """

    name = serializers.CharField(required=False, allow_blank=True)
    tax_id = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class SupplierSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    tax_id = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    notes = serializers.CharField(read_only=True)
    active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
