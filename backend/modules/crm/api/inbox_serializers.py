from rest_framework import serializers

from modules.crm.application.inbox_services import InboxItem
from modules.crm.application.ports import InboxMessage

from .lead_serializers import timestamp


class MessageInputSerializer(serializers.Serializer):
    """Forma: texto libre o plantilla; la ventana y la aprobación de la plantilla las valida el caso de uso."""
    type = serializers.ChoiceField(choices=('text', 'template'))
    body = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False, max_length=4096)
    template_id = serializers.UUIDField(required=False)
    components = serializers.ListField(child=serializers.DictField(), required=False)

    def validate(self, attrs):
        if attrs['type'] == 'text' and 'body' not in attrs:
            raise serializers.ValidationError({'body': ['Escribe el mensaje.']})
        if attrs['type'] == 'template' and 'template_id' not in attrs:
            raise serializers.ValidationError({'template_id': ['Elige una plantilla.']})
        return attrs


class OwnerInputSerializer(serializers.Serializer):
    owner_id = serializers.IntegerField(allow_null=True)


class ContactInputSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    lead_id = serializers.UUIDField(required=False, allow_null=True)


class OpportunityLinkInputSerializer(serializers.Serializer):
    opportunity_id = serializers.UUIDField(allow_null=True)


class OpportunityNewInputSerializer(serializers.Serializer):
    board_id = serializers.UUIDField()
    stage_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(allow_blank=True, trim_whitespace=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    owner_id = serializers.IntegerField(required=False, allow_null=True)


def _preview(m: InboxMessage) -> str:
    if m.type == 'text':
        return str(m.content.get('body', ''))[:120]
    if m.type == 'template':
        return str(m.content.get('name', ''))
    return f'[{m.type}]'


def message_data(m: InboxMessage) -> dict:
    return {'id': str(m.id), 'direction': m.direction, 'type': m.type, 'content': m.content, 'status': m.status,
            'failure_reason': m.failure_reason, 'created_at': timestamp(m.created_at), 'sent_at': timestamp(m.sent_at)}


def conversation_data(item: InboxItem) -> dict:
    c, last = item.conversation, item.conversation.last_message
    data = {
        'id': str(c.id), 'phone': c.phone,
        'contact': {'type': item.contact.type, 'id': str(item.contact.id), 'name': item.contact.name}
        if item.contact else None,
        'owner': {'id': c.owner_id, 'name': item.owner_name} if c.owner_id else None,
        'opportunity': {'id': str(item.opportunity.id), 'title': item.opportunity.title} if item.opportunity else
        ({'id': str(c.opportunity_id), 'title': ''} if c.opportunity_id else None),
        'last_message': {'type': last.type, 'preview': _preview(last), 'direction': last.direction,
                         'status': last.status, 'at': timestamp(last.created_at)} if last else None,
        'window_open': c.window_open, 'window_expires_at': timestamp(c.window_expires_at),
    }
    if item.connection_active is not None:
        data['connection_active'] = item.connection_active
    return data
