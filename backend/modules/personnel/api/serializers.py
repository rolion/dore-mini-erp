from rest_framework import serializers


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({key: ['Campo no permitido.'] for key in unknown})
        return super().to_internal_value(data)


class SpecialtyInputSerializer(StrictInputSerializer):
    name = serializers.CharField(required=False, allow_blank=True)


class ProfessionalInputSerializer(SpecialtyInputSerializer):
    identification = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    registration_number = serializers.CharField(required=False, allow_blank=True)
    user_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    specialty_ids = serializers.ListField(child=serializers.UUIDField(), required=False)


class SpecialtySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    active = serializers.BooleanField(read_only=True)
    created_by = serializers.IntegerField(read_only=True)
    updated_by = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class SpecialtySummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    active = serializers.BooleanField(read_only=True)


class ProfessionalSerializer(SpecialtySerializer):
    identification = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    registration_number = serializers.CharField(read_only=True)
    user_id = serializers.IntegerField(read_only=True, allow_null=True)
    specialties = SpecialtySummarySerializer(many=True, read_only=True)
    specialty_ids = serializers.SerializerMethodField()

    def get_specialty_ids(self, obj):
        return [str(item.id) for item in obj.specialties.all()]


class ListFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, default='')
    active = serializers.ChoiceField(choices=('true', 'false'), required=False)
    specialty_id = serializers.UUIDField(required=False)
