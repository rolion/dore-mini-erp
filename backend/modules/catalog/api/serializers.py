from rest_framework import serializers

from modules.catalog.domain.product import CATEGORIES, NAME_MAX_LENGTH
from modules.catalog.domain.unit import ABBREVIATION_MAX_LENGTH
from modules.catalog.domain.unit import NAME_MAX_LENGTH as UNIT_NAME_MAX_LENGTH


class ProductInputSerializer(serializers.Serializer):
    """Valida forma y tipos; las reglas de negocio las aplica el dominio. `active` no es editable aquí."""

    name = serializers.CharField(max_length=NAME_MAX_LENGTH)
    description = serializers.CharField(required=False, allow_blank=True)
    sale_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False,
                                          allow_null=True)
    category = serializers.ChoiceField(choices=CATEGORIES)
    can_buy = serializers.BooleanField(required=False)
    can_sell = serializers.BooleanField(required=False)
    tracks_stock = serializers.BooleanField(required=False)
    base_unit_id = serializers.UUIDField(required=False, allow_null=True)


class BaseUnitSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    abbreviation = serializers.CharField(read_only=True)
    allows_fractions = serializers.BooleanField(read_only=True)


class ProductSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    sale_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, allow_null=True)
    category = serializers.CharField(read_only=True, allow_null=True)
    can_buy = serializers.BooleanField(read_only=True)
    can_sell = serializers.BooleanField(read_only=True)
    needs_review = serializers.BooleanField(read_only=True)
    active = serializers.BooleanField(read_only=True)
    tracks_stock = serializers.BooleanField(read_only=True)
    base_unit_id = serializers.UUIDField(read_only=True, allow_null=True)
    base_unit = BaseUnitSerializer(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class UnitInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=UNIT_NAME_MAX_LENGTH)
    abbreviation = serializers.CharField(max_length=ABBREVIATION_MAX_LENGTH)
    allows_fractions = serializers.BooleanField(required=False)


class UnitSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    abbreviation = serializers.CharField(read_only=True)
    allows_fractions = serializers.BooleanField(read_only=True)
    active = serializers.BooleanField(read_only=True)
    in_use = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
