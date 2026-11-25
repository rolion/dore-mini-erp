"""Tableros comerciales y sus etapas (puro: sin Django). Reglas INV-01…INV-05 del PLAN."""
from dataclasses import dataclass, field
from uuid import UUID, uuid4

NAME_MAX = 80


class BoardValidationError(Exception):
    """Entrada inválida (400): `errors` es `{campo: [mensajes]}`."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class BoardNotFound(Exception):
    pass


class BoardConflict(Exception):
    """Regla de negocio que impide la operación (409): `code` y datos extra para el cliente."""

    def __init__(self, code: str, message: str, **extra):
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra


def clean_name(value: object) -> str:
    name = value.strip() if isinstance(value, str) else ''
    if not name:
        raise BoardValidationError({'name': ['Ingresa un nombre.']})
    if len(name) > NAME_MAX:
        raise BoardValidationError({'name': [f'Usa como máximo {NAME_MAX} caracteres.']})
    return name


def _same(a: str, b: str) -> bool:
    return a.casefold() == b.casefold()


@dataclass
class Stage:
    id: UUID
    name: str
    position: int
    is_active: bool = True


@dataclass
class Board:
    id: UUID
    name: str
    is_active: bool = True
    stages: list[Stage] = field(default_factory=list)

    @classmethod
    def create(cls, name: str) -> 'Board':
        return cls(id=uuid4(), name=clean_name(name))

    def active_stages(self) -> list[Stage]:
        return sorted((s for s in self.stages if s.is_active), key=lambda s: s.position)

    def _stage(self, stage_id: UUID, *, active: bool = True) -> Stage:
        stage = next((s for s in self.stages if s.id == stage_id), None)
        if stage is None or (active and not stage.is_active):
            raise BoardNotFound('Etapa no encontrada.')
        return stage

    def _check_stage_name(self, name: str, *, ignore: UUID | None = None) -> None:
        if any(s.is_active and s.id != ignore and _same(s.name, name) for s in self.stages):
            raise BoardValidationError({'name': ['Ya existe una etapa con este nombre en el tablero.']})

    def rename(self, name: str) -> None:
        self.name = clean_name(name)

    def add_stage(self, name: str) -> Stage:
        name = clean_name(name)
        self._check_stage_name(name)
        stage = Stage(id=uuid4(), name=name, position=len(self.active_stages()) + 1)
        self.stages.append(stage)
        return stage

    def rename_stage(self, stage_id: UUID, name: str) -> Stage:
        stage = self._stage(stage_id)
        name = clean_name(name)
        self._check_stage_name(name, ignore=stage.id)
        stage.name = name
        return stage

    def reorder(self, stage_ids: list[UUID]) -> None:
        current = {s.id for s in self.active_stages()}
        if len(stage_ids) != len(set(stage_ids)) or set(stage_ids) != current:
            raise BoardConflict('stage_order_stale',
                                'El orden enviado no coincide con las etapas activas; recarga el tablero.')
        by_id = {s.id: s for s in self.stages}
        for position, stage_id in enumerate(stage_ids, start=1):
            by_id[stage_id].position = position

    def validate_stage_archive(self, stage_id: UUID, target_stage_id: UUID | None, card_count: int) -> Stage:
        """Comprueba INV-03/INV-05 sin cambiar nada; devuelve la etapa a archivar."""
        stage = self._stage(stage_id)
        if card_count and target_stage_id is None:
            raise BoardConflict('stage_has_cards', 'La etapa tiene tarjetas: elige una etapa destino.',
                                card_count=card_count)
        if target_stage_id is not None:
            if target_stage_id == stage_id:
                raise BoardValidationError({'target_stage_id': ['La etapa destino debe ser distinta.']})
            try:
                self._stage(target_stage_id)
            except BoardNotFound:
                raise BoardValidationError({'target_stage_id': ['Elige una etapa activa de este tablero.']}) from None
        return stage

    def archive_stage(self, stage_id: UUID) -> None:
        stage = self._stage(stage_id)
        stage.is_active = False
        for position, active in enumerate(self.active_stages(), start=1):
            active.position = position

    def archive(self, card_count: int = 0) -> None:
        if card_count:
            raise BoardConflict('board_has_cards', 'El tablero tiene tarjetas y no se puede archivar.',
                                card_count=card_count)
        self.is_active = False

    def reactivate(self) -> None:
        self.is_active = True
