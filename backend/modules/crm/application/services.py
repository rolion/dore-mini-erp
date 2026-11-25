from uuid import UUID

from modules.crm.domain.board import Board, BoardNotFound

from .ports import StageCards


class BoardService:
    """Casos de uso de tableros y etapas. El llamador abre la transacción; las escrituras bloquean el tablero."""

    def __init__(self, repository, cards: StageCards):
        self.repository, self.cards = repository, cards

    def card_count(self, board: Board) -> int:
        return sum(self.cards.count(stage.id) for stage in board.active_stages())

    def _locked(self, board_id: UUID) -> Board:
        board = self.repository.get(board_id, for_update=True)
        if board is None:
            raise BoardNotFound('Tablero no encontrado.')
        return board

    def get(self, board_id: UUID) -> Board:
        board = self.repository.get(board_id)
        if board is None:
            raise BoardNotFound('Tablero no encontrado.')
        return board

    def list(self, *, active: bool | None = None) -> "list[Board]":
        return self.repository.list(active=active)

    def create(self, name: str) -> Board:
        return self.repository.save(Board.create(name))

    def rename(self, board_id: UUID, name: str) -> Board:
        board = self._locked(board_id)
        board.rename(name)
        return self.repository.save(board)

    def archive(self, board_id: UUID) -> Board:
        board = self._locked(board_id)
        board.archive(self.card_count(board))
        return self.repository.save(board)

    def reactivate(self, board_id: UUID) -> Board:
        board = self._locked(board_id)
        board.reactivate()
        return self.repository.save(board)

    def add_stage(self, board_id: UUID, name: str) -> Board:
        board = self._locked(board_id)
        board.add_stage(name)
        return self.repository.save(board)

    def rename_stage(self, board_id: UUID, stage_id: UUID, name: str) -> Board:
        board = self._locked(board_id)
        board.rename_stage(stage_id, name)
        return self.repository.save(board)

    def reorder(self, board_id: UUID, stage_ids: "list[UUID]") -> Board:
        board = self._locked(board_id)
        board.reorder(stage_ids)
        return self.repository.save(board)

    def archive_stage(self, board_id: UUID, stage_id: UUID, target_stage_id: UUID | None = None) -> Board:
        """Reasigna las tarjetas y archiva la etapa; atómico con la transacción del llamador."""
        board = self._locked(board_id)
        count = self.cards.count(stage_id) if any(s.id == stage_id for s in board.stages) else 0
        board.validate_stage_archive(stage_id, target_stage_id, count)
        if count:
            self.cards.reassign(stage_id, target_stage_id)
        board.archive_stage(stage_id)
        return self.repository.save(board)
