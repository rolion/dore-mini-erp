from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers

from modules.accounts.models import User


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class RegisterSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=150, validators=[UnicodeUsernameValidator()])
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(trim_whitespace=False, max_length=128, write_only=True)


class UserSerializer(serializers.ModelSerializer):
    company = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'role', 'company')
        read_only_fields = fields

    def get_company(self, user: User) -> dict | None:
        if user.company is None:
            return None
        return {'id': str(user.company.id), 'name': user.company.name}
