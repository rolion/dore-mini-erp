"""Casos de uso de oportunidades (AC-02…AC-04, AC-06, AC-07). El llamador abre la transacción; las escrituras
bloquean la fila de la oportunidad."""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from modules.crm.domain.board import Board
from modules.crm.domain.errors import CrmConflict, CrmNotFound, CrmValidationError
from modules.crm.domain.lead import Lead
from modules.crm.domain.opportunity import LOST, WON, Opportunity, StageChange

from .ports import Clock, CustomerContact, CustomerGateway, ModuleAvailability, OrderGateway, OrderRef, UserDirectory

UNSET = object()


@dataclass(frozen=True)
class OpportunityCard:
    """Oportunidad con su contacto y responsable resueltos (por lote en los listados)."""
    opportunity: Opportunity
    lead: Lead | None
    customer: CustomerContact | None
    owner_name: str


class OpportunityRows:
    """Filas paginables: contactos y responsables se piden solo para la página pedida, en lote (sin N+1)."""

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


class OpportunityService:
    def __init__(self, *, opportunities, boards, leads, customers: CustomerGateway, users: UserDirectory,
                 orders: OrderGateway, availability: ModuleAvailability, clock: Clock):
        self.opportunities, self.boards, self.leads = opportunities, boards, leads
        self.customers, self.users, self.orders = customers, users, orders
        self.availability, self.clock = availability, clock

    # --- lectura -------------------------------------------------------------------------------------------

    def describe(self, opportunities: Sequence[Opportunity]) -> list[OpportunityCard]:
        leads = self.leads.get_many({o.lead_id for o in opportunities if o.lead_id})
        customers = self.customers.get_many({o.customer_id for o in opportunities if o.customer_id})
        owners = self.users.names({o.owner_id for o in opportunities})
        return [OpportunityCard(o, leads.get(o.lead_id), customers.get(o.customer_id), owners.get(o.owner_id, ''))
                for o in opportunities]

    def card(self, opportunity: Opportunity) -> OpportunityCard:
        return self.describe([opportunity])[0]

    def _board(self, board_id: UUID) -> Board:
        board = self.boards.get(board_id)
        if board is None:
            raise CrmNotFound('Tablero no encontrado.')
        return board

    def _get(self, opportunity_id: UUID, *, for_update: bool = False) -> Opportunity:
        opportunity = self.opportunities.get(opportunity_id, for_update=for_update)
        if opportunity is None:
            raise CrmNotFound('Oportunidad no encontrada.')
        return opportunity

    def get(self, opportunity_id: UUID) -> Opportunity:
        return self._get(opportunity_id)

    def list(self, *, board_id: UUID, owner_id: int | None = None, lead_id: UUID | None = None,
             customer_id: UUID | None = None, status: str | None = None) -> OpportunityRows:
        """El tablero debe ser de la empresa (404); los demás filtros solo acotan dentro de la empresa."""
        self._board(board_id)
        rows = self.opportunities.list(board_id=board_id, owner_id=owner_id, lead_id=lead_id,
                                       customer_id=customer_id, status=status)
        return OpportunityRows(rows, self.describe)

    def history(self, opportunity_id: UUID) -> "list[StageChange]":
        self._get(opportunity_id)
        return self.opportunities.history(opportunity_id)

    # --- escritura -----------------------------------------------------------------------------------------

    def _owner(self, owner_id: int | None, actor_id: int) -> int:
        if owner_id is None:
            return actor_id
        if not self.users.exists(owner_id):
            raise CrmValidationError({'owner_id': ['Elige un usuario de tu empresa.']})
        return owner_id

    def _stage_of(self, board: Board, stage_id: UUID | None) -> UUID:
        active = board.active_stages()
        if stage_id is None:
            if not active:
                raise CrmConflict('board_has_no_stages', 'El tablero no tiene etapas activas: agrega una primero.')
            return active[0].id
        if not any(s.id == stage_id for s in board.stages) and not self.opportunities.stage_in_company(stage_id):
            raise CrmNotFound('Etapa no encontrada.')
        if not any(s.id == stage_id for s in active):
            raise CrmValidationError({'stage_id': ['Elige una etapa activa de este tablero.']})
        return stage_id

    def _record(self, opportunity_id: UUID, from_stage: UUID | None, to_stage: UUID, actor_id: int | None) -> None:
        self.opportunities.add_stage_change(StageChange(opportunity_id, from_stage, to_stage, actor_id, self.clock()))

    def create(self, *, actor_id: int, board_id: UUID, title: object, amount: object, stage_id: UUID | None = None,
               lead_id: UUID | None = None, customer_id: UUID | None = None, next_action_at: datetime | None = None,
               owner_id: int | None = None) -> Opportunity:
        board = self._board(board_id)
        if not board.is_active:
            raise CrmValidationError({'board_id': ['El tablero está archivado.']})
        lead = self.leads.get(lead_id) if lead_id is not None else None
        if lead_id is not None and lead is None:
            raise CrmNotFound('Prospecto no encontrado.')
        if customer_id is not None:
            self._active_customer(customer_id)
        elif lead is not None and lead.converted_customer_id is not None:
            customer_id = lead.converted_customer_id  # prospecto ya convertido: la oportunidad nace con su cliente
        owner = self._owner(owner_id, actor_id)
        stage = self._stage_of(board, stage_id)
        opportunity = Opportunity.create(board_id=board.id, stage_id=stage, lead_id=lead_id, customer_id=customer_id,
                                         title=title, amount=amount, owner_id=owner, next_action_at=next_action_at)
        opportunity = self.opportunities.save(opportunity)
        self._record(opportunity.id, None, stage, actor_id)
        return opportunity

    def _active_customer(self, customer_id: UUID) -> CustomerContact:
        customer = self.customers.get(customer_id)
        if customer is None:
            raise CrmNotFound('Cliente no encontrado.')
        if not customer.active:
            raise CrmValidationError({'customer_id': ['El cliente está inactivo.']})
        return customer

    def edit(self, opportunity_id: UUID, *, actor_id: int, title: object = UNSET, amount: object = UNSET,
             next_action_at: object = UNSET, owner_id: object = UNSET) -> Opportunity:
        opportunity = self._get(opportunity_id, for_update=True)
        owner = None
        if owner_id is not UNSET:
            owner = self._owner(owner_id, actor_id) if owner_id is not None else actor_id
        opportunity.edit(title=None if title is UNSET else title, amount=None if amount is UNSET else amount,
                         owner_id=owner, next_action_at=None if next_action_at is UNSET else next_action_at,
                         change_next_action=next_action_at is not UNSET)
        return self.opportunities.save(opportunity)

    def move(self, opportunity_id: UUID, stage_id: UUID, *, actor_id: int) -> Opportunity:
        opportunity = self._get(opportunity_id, for_update=True)
        board = self._board(opportunity.board_id)
        if not any(s.id == stage_id for s in board.stages) and not self.opportunities.stage_in_company(stage_id):
            raise CrmNotFound('Etapa no encontrada.')
        previous = opportunity.move_to(stage_id, {s.id for s in board.active_stages()})
        if previous is None:
            return opportunity
        opportunity = self.opportunities.save(opportunity)
        self._record(opportunity.id, previous, stage_id, actor_id)
        return opportunity

    def close(self, opportunity_id: UUID, result: str, *, lost_reason: object = '',
              order_id: UUID | None = None) -> Opportunity:
        """Cierre idempotente (INV-03): repetir el mismo resultado no cambia `closed_at`."""
        opportunity = self._get(opportunity_id, for_update=True)
        if result == WON:
            changed = opportunity.close_won(self.clock())
            if order_id is not None:
                changed = self._apply_order(opportunity, order_id) or changed
        elif result == LOST:
            if order_id is not None:
                raise CrmValidationError({'order_id': ['Solo una oportunidad ganada puede vincular un pedido.']})
            changed = opportunity.close_lost(lost_reason, self.clock())
        else:
            raise CrmValidationError({'result': ['Usa won o lost.']})
        return self.opportunities.save(opportunity) if changed else opportunity

    def link_order(self, opportunity_id: UUID, order_id: UUID) -> Opportunity:
        opportunity = self._get(opportunity_id, for_update=True)
        changed = self._apply_order(opportunity, order_id)
        return self.opportunities.save(opportunity) if changed else opportunity

    def _require_sales(self) -> None:
        if not self.availability.sales_enabled():
            raise CrmConflict('sales_disabled', 'Habilita Ventas para vincular pedidos.')

    def _apply_order(self, opportunity: Opportunity, order_id: UUID) -> bool:
        """Reglas de vínculo (INV-06): Ventas habilitado, pedido de la empresa, mismo cliente, no cancelado, único."""
        self._require_sales()
        order = self.orders.get(order_id)
        if order is None:
            raise CrmNotFound('Pedido no encontrado.')
        changed = opportunity.link_order(order.id, order.customer_id, order.cancelled)
        other = self.opportunities.opportunity_for_order(order.id)
        if other is not None and other != opportunity.id:
            raise CrmConflict('order_already_linked', 'El pedido ya está vinculado a otra oportunidad.')
        return changed

    def linkable_orders(self, opportunity_id: UUID) -> "list[OrderRef]":
        """Pedidos del cliente de la oportunidad no cancelados y sin otra oportunidad (selector de la UI)."""
        opportunity = self._get(opportunity_id)
        self._require_sales()
        if opportunity.customer_id is None:
            raise CrmConflict('customer_required', 'Convierte el prospecto en cliente antes de vincular un pedido.')
        orders = list(self.orders.list_for_customer(opportunity.customer_id))
        taken = self.opportunities.linked_order_ids([o.id for o in orders if o.id != opportunity.order_id])
        return [o for o in orders if o.id not in taken]
