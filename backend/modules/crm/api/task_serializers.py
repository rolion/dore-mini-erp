from rest_framework import serializers

from modules.crm.application.activity_services import ActivityCard
from modules.crm.application.related import RelatedRef
from modules.crm.application.task_services import TaskCard
from modules.crm.domain.activity import CHANNELS, OUTCOMES

from .lead_serializers import timestamp


class ActivityFieldsMixin(serializers.Serializer):
    """Forma y tipos; las reglas (resultado o notas, fecha no futura) son del dominio."""
    channel = serializers.ChoiceField(choices=CHANNELS)
    outcome = serializers.ChoiceField(choices=OUTCOMES, required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True, trim_whitespace=False)
    occurred_at = serializers.DateTimeField(required=False, allow_null=True)


class ActivityCreateInputSerializer(ActivityFieldsMixin):
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    opportunity_id = serializers.UUIDField(required=False, allow_null=True)


class TaskCreateInputSerializer(serializers.Serializer):
    title = serializers.CharField(allow_blank=True, trim_whitespace=False)
    due_at = serializers.DateTimeField()
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    opportunity_id = serializers.UUIDField(required=False, allow_null=True)
    owner_id = serializers.IntegerField(required=False, allow_null=True)


class TaskEditInputSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    due_at = serializers.DateTimeField(required=False)
    owner_id = serializers.IntegerField(required=False, allow_null=True)


class TaskCompleteInputSerializer(serializers.Serializer):
    activity = ActivityFieldsMixin(required=False, allow_null=True)


def related_data(related: RelatedRef) -> dict:
    return {'type': related.type, 'id': str(related.id), 'name': related.name}


def task_data(card: TaskCard) -> dict:
    t = card.task
    return {
        'id': str(t.id), 'title': t.title, 'related': related_data(card.related),
        'owner': {'id': t.owner_id, 'name': card.owner_name}, 'due_at': timestamp(t.due_at), 'status': t.status,
        'is_overdue': card.is_overdue, 'completed_at': timestamp(t.completed_at), 'created_at': timestamp(t.created_at),
    }


def activity_data(card: ActivityCard) -> dict:
    a = card.activity
    return {
        'id': str(a.id), 'customer_id': str(a.customer_id) if a.customer_id else None,
        'opportunity_id': str(a.opportunity_id) if a.opportunity_id else None,
        'task_id': str(a.task_id) if a.task_id else None, 'actor': {'id': a.actor_id, 'name': card.actor_name},
        'channel': a.channel, 'outcome': a.outcome, 'notes': a.notes, 'occurred_at': timestamp(a.occurred_at),
        'created_at': timestamp(a.created_at),
    }
