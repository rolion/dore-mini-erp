from collections.abc import Collection, Iterable
from datetime import datetime
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet

from modules.crm.domain.board import Board, BoardValidationError, Stage
from modules.crm.domain.activity import Activity
from modules.crm.domain.errors import CrmConflict
from modules.crm.domain.lead import Lead
from modules.crm.domain.opportunity import OPEN, Opportunity, StageChange
from modules.crm.domain.task import ARCHIVED, CANCELLED, DONE, PENDING, Task

from .models import (
    ActivityModel,
    BoardModel,
    LeadModel,
    OpportunityModel,
    StageChangeModel,
    StageModel,
    TaskModel,
)

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


class _Rows:
    """Vista perezosa paginable sobre un queryset: `count()` y rebanadas devuelven entidades de dominio."""

    def __init__(self, queryset: QuerySet, convert):
        self._queryset, self._convert = queryset, convert

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self._convert(model) for model in self._queryset[index]]
        return self._convert(self._queryset[index])

    def __iter__(self):
        return (self._convert(model) for model in self._queryset)


def lead_to_entity(model: LeadModel) -> Lead:
    return Lead(id=model.id, name=model.name, phone=model.phone, normalized_phone=model.normalized_phone,
                email=model.email, converted_customer_id=model.converted_customer_id, created_at=model.created_at)


class DjangoLeadRepository:
    """Prospectos de la empresa del usuario autenticado; un id ajeno nunca resuelve."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _leads(self) -> QuerySet:
        return LeadModel.objects.filter(company_id=self.company_id)

    def get(self, lead_id: UUID, *, for_update: bool = False) -> Lead | None:
        queryset = self._leads().select_for_update() if for_update else self._leads()
        model = queryset.filter(pk=lead_id).first()
        return lead_to_entity(model) if model else None

    def get_many(self, lead_ids: Iterable[UUID]) -> dict[UUID, Lead]:
        ids = set(lead_ids)
        if not ids:
            return {}
        return {m.id: lead_to_entity(m) for m in self._leads().filter(pk__in=ids)}

    def list(self, *, search: str | None = None, converted: bool | None = None) -> _Rows:
        queryset = self._leads().order_by('-created_at', 'id')
        if search:
            condition = Q(name__icontains=search) | Q(phone__icontains=search) | Q(email__icontains=search)
            digits = ''.join(ch for ch in search if ch.isdigit())
            if digits:
                condition |= Q(normalized_phone__contains=digits)
            queryset = queryset.filter(condition)
        if converted is not None:
            queryset = queryset.filter(converted_customer_id__isnull=not converted)
        return _Rows(queryset, lead_to_entity)

    def save(self, lead: Lead) -> Lead:
        LeadModel.objects.update_or_create(
            company_id=self.company_id, pk=lead.id,
            defaults={'name': lead.name, 'phone': lead.phone, 'normalized_phone': lead.normalized_phone,
                      'email': lead.email, 'converted_customer_id': lead.converted_customer_id})
        return self.get(lead.id)


def opportunity_to_entity(model: OpportunityModel) -> Opportunity:
    return Opportunity(
        id=model.id, board_id=model.board_id, stage_id=model.stage_id, lead_id=model.lead_id,
        customer_id=model.customer_id, title=model.title, owner_id=model.owner_id, amount=model.amount,
        currency=model.currency, next_action_at=model.next_action_at, status=model.status,
        closed_at=model.closed_at, order_id=model.order_id, lost_reason=model.lost_reason,
        created_at=model.created_at, description=model.description)


def _stage_change(model: StageChangeModel) -> StageChange:
    return StageChange(opportunity_id=model.opportunity_id, from_stage_id=model.from_stage_id,
                       to_stage_id=model.to_stage_id, changed_by=model.changed_by, changed_at=model.changed_at)


class DjangoOpportunityRepository:
    """Oportunidades de la empresa; tableros, etapas y prospectos referidos se validan en la misma empresa."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _opportunities(self) -> QuerySet:
        return OpportunityModel.objects.filter(company_id=self.company_id)

    def get(self, opportunity_id: UUID, *, for_update: bool = False) -> Opportunity | None:
        queryset = self._opportunities()
        if for_update:
            # Bloquea la fila: serializa cerrar/mover/vincular de dos personas a la vez.
            queryset = queryset.select_for_update()
        model = queryset.filter(pk=opportunity_id).first()
        return opportunity_to_entity(model) if model else None

    def get_many(self, opportunity_ids: Iterable[UUID]) -> dict[UUID, Opportunity]:
        ids = set(opportunity_ids)
        if not ids:
            return {}
        return {m.id: opportunity_to_entity(m) for m in self._opportunities().filter(pk__in=ids)}

    def list(self, *, board_id: UUID, owner_id: int | None = None, lead_id: UUID | None = None,
             customer_id: UUID | None = None, status: str | None = None) -> _Rows:
        queryset = self._opportunities().filter(board_id=board_id).order_by('created_at', 'id')
        if owner_id is not None:
            queryset = queryset.filter(owner_id=owner_id)
        if lead_id is not None:
            queryset = queryset.filter(lead_id=lead_id)
        if customer_id is not None:
            queryset = queryset.filter(customer_id=customer_id)
        if status is not None:
            queryset = queryset.filter(status=status)
        return _Rows(queryset, opportunity_to_entity)

    def open_for_lead(self, lead_id: UUID) -> "list[Opportunity]":
        queryset = self._opportunities().filter(lead_id=lead_id, status=OPEN).select_for_update()
        return [opportunity_to_entity(m) for m in queryset.order_by('created_at', 'id')]

    def stage_in_company(self, stage_id: UUID) -> bool:
        return StageModel.objects.filter(pk=stage_id, board__company_id=self.company_id).exists()

    def opportunity_for_order(self, order_id: UUID) -> UUID | None:
        """Oportunidad que ya usa el pedido (en cualquier empresa: el pedido es único en todo el sistema)."""
        return OpportunityModel.objects.filter(order_id=order_id).values_list('id', flat=True).first()

    def linked_order_ids(self, order_ids: Collection[UUID]) -> set[UUID]:
        return set(OpportunityModel.objects.filter(order_id__in=list(order_ids)).values_list('order_id', flat=True))

    def save(self, opportunity: Opportunity) -> Opportunity:
        values = {
            'board_id': opportunity.board_id, 'stage_id': opportunity.stage_id, 'lead_id': opportunity.lead_id,
            'customer_id': opportunity.customer_id, 'title': opportunity.title, 'owner_id': opportunity.owner_id,
            'amount': opportunity.amount, 'currency': opportunity.currency,
            'next_action_at': opportunity.next_action_at, 'status': opportunity.status,
            'closed_at': opportunity.closed_at, 'order_id': opportunity.order_id,
            'lost_reason': opportunity.lost_reason, 'description': opportunity.description,
        }
        try:
            # Savepoint: un pedido vinculado en carrera choca con la restricción única sin romper la transacción.
            with transaction.atomic():
                OpportunityModel.objects.update_or_create(company_id=self.company_id, pk=opportunity.id,
                                                          defaults=values)
        except IntegrityError as exc:
            name = getattr(getattr(exc.__cause__, 'diag', None), 'constraint_name', None)
            if name != 'crm_opportunity_order_unique':
                raise
            raise CrmConflict('order_already_linked', 'El pedido ya está vinculado a otra oportunidad.') from exc
        return self.get(opportunity.id)

    def add_stage_change(self, change: StageChange) -> None:
        StageChangeModel.objects.create(
            opportunity_id=change.opportunity_id, from_stage_id=change.from_stage_id,
            to_stage_id=change.to_stage_id, changed_by=change.changed_by, changed_at=change.changed_at)

    def history(self, opportunity_id: UUID) -> "list[StageChange]":
        queryset = StageChangeModel.objects.filter(
            opportunity_id=opportunity_id, opportunity__company_id=self.company_id).order_by('changed_at', 'id')
        return [_stage_change(m) for m in queryset]


class DjangoStageCards:
    """Puerto `StageCards` real: las tarjetas son las oportunidades **abiertas** de la etapa (INV-09).

    Reasignar mueve solo abiertas y deja un `StageChange` por cada una (sin autor: lo hace el sistema).
    Corre en la transacción de quien llama (`BoardService.archive_stage`).
    """

    def __init__(self, company_id: UUID, clock):
        self.company_id, self.clock = company_id, clock

    def _open(self, stage_id: UUID) -> QuerySet:
        return OpportunityModel.objects.filter(company_id=self.company_id, stage_id=stage_id, status=OPEN)

    def count(self, stage_id: UUID) -> int:
        return self._open(stage_id).count()

    def reassign(self, from_stage_id: UUID, to_stage_id: UUID) -> int:
        ids = list(self._open(from_stage_id).select_for_update().values_list('id', flat=True))
        if not ids:
            return 0
        now = self.clock()
        OpportunityModel.objects.filter(pk__in=ids).update(stage_id=to_stage_id, updated_at=now)
        StageChangeModel.objects.bulk_create([
            StageChangeModel(opportunity_id=pk, from_stage_id=from_stage_id, to_stage_id=to_stage_id,
                             changed_by=None, changed_at=now) for pk in ids])
        return len(ids)


def task_to_entity(model: TaskModel) -> Task:
    return Task(id=model.id, customer_id=model.customer_id, opportunity_id=model.opportunity_id,
                title=model.title, owner_id=model.owner_id, due_at=model.due_at, status=model.status,
                completed_at=model.completed_at, created_at=model.created_at)


class DjangoTaskRepository:
    """Tareas de la empresa; las archivadas nunca se listan (INV-08) aunque se pueden leer por id."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _tasks(self) -> QuerySet:
        return TaskModel.objects.filter(company_id=self.company_id)

    def get(self, task_id: UUID, *, for_update: bool = False) -> Task | None:
        queryset = self._tasks().select_for_update() if for_update else self._tasks()
        model = queryset.filter(pk=task_id).first()
        return task_to_entity(model) if model else None

    def list(self, *, now: datetime, owner_id: int | None = None, status: str | None = None,
             customer_id: UUID | None = None, opportunity_id: UUID | None = None) -> _Rows:
        queryset = self._tasks().exclude(status=ARCHIVED).order_by('due_at', 'created_at', 'id')
        if status == 'overdue':
            queryset = queryset.filter(status=PENDING, due_at__lt=now)
        elif status in (PENDING, DONE, CANCELLED):
            queryset = queryset.filter(status=status)
        if owner_id is not None:
            queryset = queryset.filter(owner_id=owner_id)
        if customer_id is not None:
            queryset = queryset.filter(customer_id=customer_id)
        if opportunity_id is not None:
            queryset = queryset.filter(opportunity_id=opportunity_id)
        return _Rows(queryset, task_to_entity)

    def save(self, task: Task) -> Task:
        TaskModel.objects.update_or_create(
            company_id=self.company_id, pk=task.id,
            defaults={'customer_id': task.customer_id, 'opportunity_id': task.opportunity_id, 'title': task.title,
                      'owner_id': task.owner_id, 'due_at': task.due_at, 'status': task.status,
                      'completed_at': task.completed_at})
        return self.get(task.id)


def activity_to_entity(model: ActivityModel) -> Activity:
    return Activity(id=model.id, actor_id=model.actor_id, customer_id=model.customer_id,
                    opportunity_id=model.opportunity_id, channel=model.channel, outcome=model.outcome,
                    notes=model.notes, occurred_at=model.occurred_at, task_id=model.task_id,
                    created_at=model.created_at)


class DjangoActivityRepository:
    """Actividades de la empresa: solo `add` y lectura (inmutables)."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def add(self, activity: Activity) -> Activity:
        model = ActivityModel.objects.create(
            id=activity.id, company_id=self.company_id, actor_id=activity.actor_id,
            customer_id=activity.customer_id, opportunity_id=activity.opportunity_id, task_id=activity.task_id,
            channel=activity.channel, outcome=activity.outcome, notes=activity.notes,
            occurred_at=activity.occurred_at)
        return activity_to_entity(model)

    def list(self, *, customer_id: UUID | None = None, opportunity_id: UUID | None = None) -> _Rows:
        queryset = ActivityModel.objects.filter(company_id=self.company_id).order_by(
            '-occurred_at', '-created_at', 'id')
        if customer_id is not None:
            queryset = queryset.filter(customer_id=customer_id)
        if opportunity_id is not None:
            queryset = queryset.filter(opportunity_id=opportunity_id)
        return _Rows(queryset, activity_to_entity)
