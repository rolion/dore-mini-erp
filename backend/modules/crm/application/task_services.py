"""Casos de uso de tareas comerciales (AC-01…AC-06). El llamador abre la transacción; las escrituras de estado
bloquean la fila de la tarea."""
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from modules.crm.domain.activity import Activity
from modules.crm.domain.errors import CrmNotFound, CrmValidationError
from modules.crm.domain.task import Task

from .ports import Clock, UserDirectory
from .related import RelatedEntities, RelatedRef

STATUS_FILTERS = ('pending', 'done', 'cancelled', 'overdue', 'all')


@dataclass(frozen=True)
class TaskCard:
    task: Task
    related: RelatedRef
    owner_name: str
    is_overdue: bool


class TaskRows:
    """Filas paginables: relacionados y responsables se piden solo para la página pedida, en lote."""

    def __init__(self, rows, describe):
        self._rows, self._describe = rows, describe

    def count(self) -> int:
        return self._rows.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if not isinstance(index, slice):
            return self[index:index + 1][0]
        return self._describe(self._rows[index])


class TaskService:
    def __init__(self, *, tasks, activities, related: RelatedEntities, users: UserDirectory, clock: Clock):
        self.tasks, self.activities, self.related, self.users, self.clock = tasks, activities, related, users, clock

    # --- lectura -------------------------------------------------------------------------------------------

    def describe(self, tasks: Sequence[Task]) -> list[TaskCard]:
        refs = self.related.refs((t.customer_id, t.opportunity_id) for t in tasks)
        owners = self.users.names({t.owner_id for t in tasks})
        now = self.clock()
        return [TaskCard(t, refs[(t.customer_id, t.opportunity_id)], owners.get(t.owner_id, ''), t.is_overdue(now))
                for t in tasks]

    def card(self, task: Task) -> TaskCard:
        return self.describe([task])[0]

    def _get(self, task_id: UUID, *, for_update: bool = False) -> Task:
        task = self.tasks.get(task_id, for_update=for_update)
        if task is None:
            raise CrmNotFound('Tarea no encontrada.')
        return task

    def get(self, task_id: UUID) -> Task:
        return self._get(task_id)

    def list(self, *, owner_id: int | None = None, status: str | None = None, customer_id: UUID | None = None,
             opportunity_id: UUID | None = None) -> TaskRows:
        rows = self.tasks.list(now=self.clock(), owner_id=owner_id, status=status, customer_id=customer_id,
                               opportunity_id=opportunity_id)
        return TaskRows(rows, self.describe)

    # --- escritura -----------------------------------------------------------------------------------------

    def _owner(self, owner_id: int | None, actor_id: int) -> int:
        if owner_id is None:
            return actor_id
        if not self.users.exists(owner_id):
            raise CrmValidationError({'owner_id': ['Elige un usuario de tu empresa.']})
        return owner_id

    def create(self, *, actor_id: int, title: object, due_at: object, customer_id: UUID | None = None,
               opportunity_id: UUID | None = None, owner_id: int | None = None) -> Task:
        self.related.require(customer_id, opportunity_id, for_new_task=True)
        owner = self._owner(owner_id, actor_id)
        task = Task.create(customer_id=customer_id, opportunity_id=opportunity_id, title=title, due_at=due_at,
                           owner_id=owner)
        return self.tasks.save(task)

    def edit(self, task_id: UUID, *, title: object = None, due_at: object = None,
             owner_id: int | None = None) -> Task:
        task = self._get(task_id, for_update=True)
        if owner_id is not None:
            self._owner(owner_id, owner_id)
        task.edit(title=title, due_at=due_at, owner_id=owner_id)
        return self.tasks.save(task)

    def complete(self, task_id: UUID, *, actor_id: int, activity: dict | None = None) -> tuple[Task, Activity | None]:
        """Completa y, si se pide, registra la actividad en la misma transacción; si la actividad es inválida no
        se completa nada."""
        task = self._get(task_id, for_update=True)
        now = self.clock()
        task.complete(now)
        recorded = None
        if activity is not None:
            self.related.require(task.customer_id, task.opportunity_id)  # INV-07: cliente inactivo no admite actividad
            recorded = self.activities.add(Activity.create(
                actor_id=actor_id, customer_id=task.customer_id, opportunity_id=task.opportunity_id,
                channel=activity.get('channel'), outcome=activity.get('outcome'), notes=activity.get('notes'),
                occurred_at=activity.get('occurred_at'), now=now, task_id=task.id))
        return self.tasks.save(task), recorded

    def cancel(self, task_id: UUID) -> Task:
        task = self._get(task_id, for_update=True)
        task.cancel()
        return self.tasks.save(task)

    def reopen(self, task_id: UUID) -> Task:
        task = self._get(task_id, for_update=True)
        task.reopen()
        return self.tasks.save(task)

    def archive(self, task_id: UUID) -> Task:
        task = self._get(task_id, for_update=True)
        task.archive()
        return self.tasks.save(task)
