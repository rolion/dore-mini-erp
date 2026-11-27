"""Casos de uso de actividad comercial (AC-07): registrar y consultar; nunca editar ni borrar."""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from modules.crm.domain.activity import Activity
from modules.crm.domain.errors import CrmValidationError

from .ports import Clock, UserDirectory
from .related import RelatedEntities


@dataclass(frozen=True)
class ActivityCard:
    activity: Activity
    actor_name: str


class ActivityRows:
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


class ActivityService:
    def __init__(self, *, activities, related: RelatedEntities, users: UserDirectory, clock: Clock):
        self.activities, self.related, self.users, self.clock = activities, related, users, clock

    def describe(self, activities: Sequence[Activity]) -> list[ActivityCard]:
        names = self.users.names({a.actor_id for a in activities})
        return [ActivityCard(a, names.get(a.actor_id, '')) for a in activities]

    def card(self, activity: Activity) -> ActivityCard:
        return self.describe([activity])[0]

    def create(self, *, actor_id: int, channel: object, outcome: object = '', notes: object = '',
               occurred_at: datetime | None = None, customer_id: UUID | None = None,
               opportunity_id: UUID | None = None) -> Activity:
        self.related.require(customer_id, opportunity_id)
        return self.activities.add(Activity.create(
            actor_id=actor_id, customer_id=customer_id, opportunity_id=opportunity_id, channel=channel,
            outcome=outcome, notes=notes, occurred_at=occurred_at, now=self.clock()))

    def list(self, *, customer_id: UUID | None = None, opportunity_id: UUID | None = None) -> ActivityRows:
        """Exige una entidad de la empresa (404 si es ajena) para no devolver «vacío» de forma engañosa."""
        if (customer_id is None) == (opportunity_id is None):
            raise CrmValidationError({'customer_id': ['Indica un cliente o una oportunidad.']})
        self.related.require_exists(customer_id, opportunity_id)
        return ActivityRows(self.activities.list(customer_id=customer_id, opportunity_id=opportunity_id),
                            self.describe)
