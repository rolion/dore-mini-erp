from rest_framework import serializers

from modules.crm.domain.board import Board


class NameInputSerializer(serializers.Serializer):
    name = serializers.CharField(allow_blank=True, trim_whitespace=False)


class StageOrderInputSerializer(serializers.Serializer):
    stage_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=True)


class StageArchiveInputSerializer(serializers.Serializer):
    target_stage_id = serializers.UUIDField(required=False, allow_null=True)


def board_data(board: Board, cards) -> dict:
    """Tablero con sus etapas activas ordenadas; `card_count` viene del puerto de tarjetas."""
    return {
        'id': str(board.id), 'name': board.name, 'is_active': board.is_active,
        'stages': [{'id': str(s.id), 'name': s.name, 'position': s.position, 'is_active': s.is_active,
                    'card_count': cards.count(s.id)} for s in board.active_stages()],
    }
