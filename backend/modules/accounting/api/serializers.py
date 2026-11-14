from rest_framework import serializers

from modules.accounting.domain.account import NAME_MAX_LENGTH


class AccountInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=False)
    currency = serializers.CharField(max_length=3)


class AccountUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=False, required=False)
    currency = serializers.CharField(max_length=3, required=False)


class MethodInputSerializer(serializers.Serializer):
    account_id = serializers.UUIDField(allow_null=True)
    is_active = serializers.BooleanField(default=True)


def serialize_account(account) -> dict:
    return {'id': str(account.id), 'name': account.name, 'currency': account.currency,
            'is_active': account.is_active, 'created_at': account.created_at, 'updated_at': account.updated_at}


def serialize_method(view) -> dict:
    account = view.account
    return {
        'code': view.code, 'label': view.label, 'is_active': view.is_active,
        'account': ({'id': str(account.id), 'name': account.name, 'currency': account.currency,
                     'is_active': account.is_active} if account else None),
    }
