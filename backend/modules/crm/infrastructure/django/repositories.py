from uuid import UUID

from django.db import IntegrityError, transaction

from modules.crm.domain.board import Board, BoardValidationError, Stage

from .models import BoardModel, StageModel

_CONSTRAINT_MESSAGES = {
    'crm_board_active_name_unique': ('name', 'Ya existe un tablero activo con este nombre en tu empresa.'),
    'crm_stage_active_name_unique': ('name', 'Ya existe una etapa con este nombre en el tablero.'),
}


def to_entity(model: BoardModel) -> Board:
    stages = [Stage(id=s.id, name=s.name, position=s.position, is_active=s.is_active) for s in model.stages.all()]
    return Board(id=model.id, name=model.name, is_active=model.is_active, stages=stages)


class DjangoBoardRepository:
    """Toda lectura/escritura filtra por la empresa del usuario autenticado; un id ajeno nunca resuelve."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _boards(self):
        return BoardModel.objects.filter(company_id=self.company_id)

    def get(self, board_id: UUID, *, for_update: bool = False) -> Board | None:
        queryset = self._boards()
        if for_update:
            # Bloquea solo la fila del tablero: serializa reordenar/archivar de dos administradores.
            queryset = queryset.select_for_update()
        model = queryset.filter(pk=board_id).first()
        return to_entity(model) if model else None

    def list(self, *, active: bool | None = None) -> "list[Board]":
        queryset = self._boards().prefetch_related('stages').order_by('created_at', 'id')
        if active is not None:
            queryset = queryset.filter(is_active=active)
        return [to_entity(model) for model in queryset]

    def save(self, board: Board) -> Board:
        try:
            # Savepoint: traduce una violación única concurrente sin envenenar la transacción de la petición.
            with transaction.atomic():
                model, _ = BoardModel.objects.update_or_create(
                    company_id=self.company_id, pk=board.id,
                    defaults={'name': board.name, 'is_active': board.is_active})
                for stage in board.stages:
                    StageModel.objects.update_or_create(
                        pk=stage.id, board=model,
                        defaults={'name': stage.name, 'position': stage.position, 'is_active': stage.is_active})
        except IntegrityError as exc:
            name = getattr(getattr(exc.__cause__, 'diag', None), 'constraint_name', None)
            if name not in _CONSTRAINT_MESSAGES:
                raise
            field, message = _CONSTRAINT_MESSAGES[name]
            raise BoardValidationError({field: [message]}) from exc
        return self.get(board.id)
