"""Tarea comercial: próxima acción con vencimiento y responsable (puro: sin Django). INV-01…INV-05, INV-08."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from .errors import CrmConflict, CrmValidationError

PENDING, DONE, CANCELLED, ARCHIVED = 'pending', 'done', 'cancelled', 'archived'
STATUSES = (PENDING, DONE, CANCELLED, ARCHIVED)
VISIBLE_STATUSES = (PENDING, DONE, CANCELLED)  # las archivadas no se muestran nunca (INV-08)
TITLE_MAX = 150


def clean_title(value: object) -> str:
    title = value.strip() if isinstance(value, str) else ''
    if not title:
        raise CrmValidationError({'title': ['Ingresa un título.']})
    if len(title) > TITLE_MAX:
        raise CrmValidationError({'title': [f'Usa como máximo {TITLE_MAX} caracteres.']})
    return title


def clean_due_at(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise CrmValidationError({'due_at': ['Indica el vencimiento.']})
    return value


def require_one_related(customer_id: UUID | None, opportunity_id: UUID | None) -> None:
    """INV-01: exactamente un cliente o una oportunidad."""
    if (customer_id is None) == (opportunity_id is None):
        raise CrmValidationError({'customer_id': ['Elige un cliente o una oportunidad, no ambos ni ninguno.']})


@dataclass
class Task:
    id: UUID
    customer_id: UUID | None
    opportunity_id: UUID | None
    title: str
    owner_id: int
    due_at: datetime
    status: str = PENDING
    completed_at: datetime | None = None
    created_at: datetime | None = None

    @classmethod
    def create(cls, *, customer_id: UUID | None, opportunity_id: UUID | None, title: object, due_at: object,
               owner_id: int) -> 'Task':
        errors: dict[str, list[str]] = {}
        try:
            require_one_related(customer_id, opportunity_id)
        except CrmValidationError as exc:
            errors.update(exc.errors)
        values = {}
        for field, check in (('title', lambda: clean_title(title)), ('due_at', lambda: clean_due_at(due_at))):
            try:
                values[field] = check()
            except CrmValidationError as exc:
                errors.update(exc.errors)
        if errors:
            raise CrmValidationError(errors)
        return cls(id=uuid4(), customer_id=customer_id, opportunity_id=opportunity_id, owner_id=owner_id, **values)

    @property
    def is_pending(self) -> bool:
        return self.status == PENDING

    def is_overdue(self, now: datetime) -> bool:
        """Vencida = pendiente con vencimiento pasado; se calcula, no es un estado."""
        return self.is_pending and self.due_at < now

    def _transition_error(self, action: str) -> CrmConflict:
        return CrmConflict('invalid_task_transition', f'No se puede {action} una tarea en estado «{self.status}».',
                           status=self.status)

    def edit(self, *, title: object = None, due_at: object = None, owner_id: int | None = None) -> None:
        """INV-04: solo una pendiente se edita; `None` = sin cambio."""
        if not self.is_pending:
            raise CrmConflict('task_not_pending', 'Solo una tarea pendiente se puede editar.', status=self.status)
        new_title = clean_title(title) if title is not None else self.title
        new_due = clean_due_at(due_at) if due_at is not None else self.due_at
        self.title, self.due_at = new_title, new_due
        if owner_id is not None:
            self.owner_id = owner_id

    def complete(self, now: datetime) -> None:
        if not self.is_pending:
            raise self._transition_error('completar')
        self.status, self.completed_at = DONE, now

    def cancel(self) -> None:
        if not self.is_pending:
            raise self._transition_error('cancelar')
        self.status = CANCELLED

    def reopen(self) -> None:
        if self.status not in (DONE, CANCELLED):
            raise self._transition_error('reabrir')
        self.status, self.completed_at = PENDING, None

    def archive(self) -> None:
        if self.status not in (DONE, CANCELLED):
            raise self._transition_error('archivar')
        self.status = ARCHIVED
