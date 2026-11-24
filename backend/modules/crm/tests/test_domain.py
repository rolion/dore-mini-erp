from uuid import uuid4

from django.test import SimpleTestCase

from modules.crm.domain.board import Board, BoardConflict, BoardNotFound, BoardValidationError


def board_with(*names):
    board = Board.create('Ventas')
    for name in names:
        board.add_stage(name)
    return board


class BoardDomainTests(SimpleTestCase):
    def test_name_is_trimmed_required_and_bounded(self):
        self.assertEqual(Board.create('  Ventas  ').name, 'Ventas')
        for bad in ('', '   ', 'x' * 81, None):
            with self.assertRaises(BoardValidationError):
                Board.create(bad)

    def test_new_board_has_no_stages_and_stages_are_appended_in_order(self):
        board = Board.create('Ventas')
        self.assertEqual(board.active_stages(), [])
        board = board_with('Nuevo', 'Ganado')
        self.assertEqual([(s.name, s.position) for s in board.active_stages()], [('Nuevo', 1), ('Ganado', 2)])

    def test_stage_names_are_unique_case_insensitive_among_active(self):
        board = board_with('Nuevo')
        with self.assertRaises(BoardValidationError):
            board.add_stage(' nuevo ')
        stage = board.add_stage('Otra')
        with self.assertRaises(BoardValidationError):
            board.rename_stage(stage.id, 'NUEVO')
        board.rename_stage(stage.id, 'Otra')  # el mismo nombre de sí misma es válido

    def test_reorder_requires_exact_active_set(self):
        board = board_with('A', 'B', 'C')
        a, b, c = (s.id for s in board.active_stages())
        board.reorder([c, a, b])
        self.assertEqual([s.name for s in board.active_stages()], ['C', 'A', 'B'])
        for bad in ([a, b], [a, b, c, uuid4()], [a, a, b], [a, b, uuid4()]):
            with self.assertRaises(BoardConflict) as ctx:
                board.reorder(bad)
            self.assertEqual(ctx.exception.code, 'stage_order_stale')
        self.assertEqual([s.name for s in board.active_stages()], ['C', 'A', 'B'])

    def test_archive_stage_recompacts_and_frees_the_name(self):
        board = board_with('A', 'B', 'C')
        a, b, c = (s.id for s in board.active_stages())
        board.archive_stage(b)
        self.assertEqual([(s.name, s.position) for s in board.active_stages()], [('A', 1), ('C', 2)])
        board.add_stage('B')  # el nombre de una archivada no bloquea
        with self.assertRaises(BoardNotFound):
            board.rename_stage(b, 'X')
        with self.assertRaises(BoardNotFound):
            board.archive_stage(b)

    def test_stage_archive_with_cards_needs_valid_target(self):
        board = board_with('A', 'B')
        a, b = (s.id for s in board.active_stages())
        with self.assertRaises(BoardConflict) as ctx:
            board.validate_stage_archive(a, None, 3)
        self.assertEqual((ctx.exception.code, ctx.exception.extra['card_count']), ('stage_has_cards', 3))
        for target in (a, uuid4()):
            with self.assertRaises(BoardValidationError):
                board.validate_stage_archive(a, target, 3)
        board.archive_stage(b)
        with self.assertRaises(BoardValidationError):  # destino archivado
            board.validate_stage_archive(a, b, 3)
        self.assertEqual(board.validate_stage_archive(a, None, 0).id, a)

    def test_board_with_cards_cannot_be_archived_and_can_be_reactivated(self):
        board = board_with('A')
        with self.assertRaises(BoardConflict) as ctx:
            board.archive(2)
        self.assertEqual(ctx.exception.code, 'board_has_cards')
        self.assertTrue(board.is_active)
        board.archive(0)
        self.assertFalse(board.is_active)
        board.reactivate()
        self.assertTrue(board.is_active)
