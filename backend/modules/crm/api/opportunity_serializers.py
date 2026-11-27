from rest_framework import serializers

from modules.crm.application.opportunity_services import OpportunityCard
from modules.crm.application.ports import OrderRef
from modules.crm.domain.opportunity import LOST, WON, StageChange

from .lead_serializers import contact_data, timestamp


def _amount_field(**kwargs):
    return serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, **kwargs)


class OpportunityCreateInputSerializer(serializers.Serializer):
    """Forma y tipos; contacto obligatorio, etapa, empresa y responsable los valida el caso de uso."""
    board_id = serializers.UUIDField()
    stage_id = serializers.UUIDField(required=False, allow_null=True)
    lead_id = serializers.UUIDField(required=False, allow_null=True)
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(allow_blank=True, trim_whitespace=False)
    amount = _amount_field(required=False)  # INV-04: sin importe se guarda 0.00
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, trim_whitespace=False)
    next_action_at = serializers.DateTimeField(required=False, allow_null=True)
    owner_id = serializers.IntegerField(required=False, allow_null=True)


class OpportunityEditInputSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    amount = _amount_field(required=False)
    description = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    next_action_at = serializers.DateTimeField(required=False, allow_null=True)
    owner_id = serializers.IntegerField(required=False, allow_null=True)


class MoveInputSerializer(serializers.Serializer):
    stage_id = serializers.UUIDField()


class CloseInputSerializer(serializers.Serializer):
    result = serializers.ChoiceField(choices=(WON, LOST))
    lost_reason = serializers.CharField(required=False, allow_blank=True, allow_null=True, trim_whitespace=False)
    order_id = serializers.UUIDField(required=False, allow_null=True)


class OrderLinkInputSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()


def _reference(ref_id, contact) -> dict | None:
    """Contacto resuelto; si ya no existe se informa al menos su id."""
    if ref_id is None:
        return None
    return contact_data(contact) or {'id': str(ref_id), 'name': '', 'phone': ''}


def opportunity_data(card: OpportunityCard) -> dict:
    o = card.opportunity
    return {
        'id': str(o.id), 'board_id': str(o.board_id), 'stage_id': str(o.stage_id),
        'lead': _reference(o.lead_id, card.lead), 'customer': _reference(o.customer_id, card.customer),
        'title': o.title, 'description': o.description, 'owner': {'id': o.owner_id, 'name': card.owner_name},
        'amount': str(o.amount), 'currency': o.currency, 'next_action_at': timestamp(o.next_action_at),
        'status': o.status, 'closed_at': timestamp(o.closed_at), 'order_id': str(o.order_id) if o.order_id else None,
        'lost_reason': o.lost_reason, 'created_at': timestamp(o.created_at),
    }


def order_data(order: OrderRef) -> dict:
    return {'id': str(order.id), 'order_date': order.order_date.isoformat(), 'total': str(order.total),
            'status': order.status}


def stage_change_data(change: StageChange) -> dict:
    return {
        'from_stage_id': str(change.from_stage_id) if change.from_stage_id else None,
        'to_stage_id': str(change.to_stage_id), 'changed_by': change.changed_by,
        'changed_at': timestamp(change.changed_at),
    }
