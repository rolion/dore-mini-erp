from rest_framework import serializers


class ConnectionInputSerializer(serializers.Serializer):
    waba_id = serializers.CharField(max_length=40)
    phone_number_id = serializers.CharField(max_length=40)
    display_phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    secret_ref = serializers.CharField(max_length=64)
    app_secret_ref = serializers.CharField(max_length=64)


class TestMessageInputSerializer(serializers.Serializer):
    to = serializers.CharField(max_length=24)
    template_id = serializers.UUIDField()


def connection_data(connection, webhook_url: str) -> dict:
    """Solo nombres de variables y datos públicos: el token y el App Secret nunca pasan por la API."""
    if connection is None:
        return {'configured': False, 'webhook_url': webhook_url}
    return {'configured': True, 'waba_id': connection.waba_id, 'phone_number_id': connection.phone_number_id,
            'display_phone': connection.display_phone, 'secret_ref': connection.secret_ref,
            'app_secret_ref': connection.app_secret_ref, 'verify_token': connection.verify_token,
            'status': connection.status, 'status_reason': connection.status_reason, 'webhook_url': webhook_url}


def template_data(t) -> dict:
    return {'id': str(t.id), 'name': t.name, 'language': t.language, 'category': t.category, 'status': t.status,
            'synced_at': t.synced_at.isoformat() if t.synced_at else None}


def message_data(m) -> dict:
    return {'id': str(m.id), 'status': m.status, 'type': m.type}
