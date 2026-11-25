"""Entidad relacionada de una tarea o actividad: un cliente o una oportunidad de la empresa (INV-01, INV-07)."""
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from modules.crm.domain.errors import CrmConflict, CrmNotFound
from modules.crm.domain.task import require_one_related

from .ports import CustomerGateway


@dataclass(frozen=True)
class RelatedRef:
    type: str  # 'customer' | 'opportunity'
    id: UUID
    name: str


class RelatedEntities:
    def __init__(self, *, customers: CustomerGateway, opportunities):
        self.customers, self.opportunities = customers, opportunities

    def require_exists(self, customer_id: UUID | None, opportunity_id: UUID | None):
        """Valida la forma (uno solo) y que exista en la empresa; un id ajeno es 404 como uno inexistente."""
        require_one_related(customer_id, opportunity_id)
        if customer_id is not None:
            customer = self.customers.get(customer_id)
            if customer is None:
                raise CrmNotFound('Cliente no encontrado.')
            return customer
        opportunity = self.opportunities.get(opportunity_id)
        if opportunity is None:
            raise CrmNotFound('Oportunidad no encontrada.')
        return opportunity

    def require(self, customer_id: UUID | None, opportunity_id: UUID | None, *, for_new_task: bool = False) -> None:
        """Además de existir: un cliente inactivo no admite tareas ni actividades nuevas, y una oportunidad cerrada
        no admite tareas nuevas (la actividad sí: es historial)."""
        found = self.require_exists(customer_id, opportunity_id)
        if customer_id is not None and not found.active:
            raise CrmConflict('customer_inactive', 'El cliente está inactivo.')
        if opportunity_id is not None and for_new_task and not found.is_open:
            raise CrmConflict('opportunity_closed', 'La oportunidad está cerrada: no admite tareas nuevas.',
                              status=found.status)

    def refs(self, pairs: Iterable[tuple[UUID | None, UUID | None]]) -> dict[tuple, RelatedRef]:
        """Nombres por lote de los relacionados de una página; clave = (customer_id, opportunity_id)."""
        pairs = list(pairs)
        customers = self.customers.get_many({c for c, _ in pairs if c})
        opportunities = self.opportunities.get_many({o for _, o in pairs if o})
        found: dict[tuple, RelatedRef] = {}
        for customer_id, opportunity_id in pairs:
            if customer_id is not None:
                contact = customers.get(customer_id)
                found[(customer_id, None)] = RelatedRef('customer', customer_id, contact.name if contact else '')
            else:
                opportunity = opportunities.get(opportunity_id)
                found[(None, opportunity_id)] = RelatedRef('opportunity', opportunity_id,
                                                           opportunity.title if opportunity else '')
        return found
